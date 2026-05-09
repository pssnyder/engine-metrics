-- ============================================================================
-- STRONGEST V7P3R VERSION ANALYSIS
-- ============================================================================
-- Purpose: Determine which v7p3r version is objectively the strongest
-- Author: ETL Validation Framework
-- Date: 2026-05-03
--
-- Methodology:
-- This query answers: "Which v7p3r version has the highest performance?"
-- by combining multiple strength indicators into a composite score.
--
-- Strength Indicators:
-- 1. Quality-Adjusted Win Rate (40% weight) - opponent-strength weighted
-- 2. Performance vs Expected (30% weight) - ELO-based overperformance
-- 3. Average V7P3R ELO (20% weight) - peak rating achieved
-- 4. Schedule Difficulty (10% weight) - quality of competition faced
-- ============================================================================

WITH version_metrics AS (
  SELECT
    gd.engine_version,
    COUNT(*) as total_games,
    
    -- Game outcomes
    COUNTIF(gd.outcome = 'win') as wins,
    COUNTIF(gd.outcome = 'loss') as losses,
    COUNTIF(gd.outcome = 'draw') as draws,
    
    -- ELO tracking
    AVG(gd.v7p3r_elo) as avg_v7p3r_elo,
    MAX(gd.v7p3r_elo) as peak_v7p3r_elo,
    AVG(gd.opponent_elo) as avg_opponent_elo,
    
    -- Game scores (win=1, draw=0.5, loss=0)
    AVG(CASE
      WHEN gd.outcome = 'win' THEN 1.0
      WHEN gd.outcome = 'draw' THEN 0.5
      ELSE 0.0
    END) as game_score,
    
    -- Quality-adjusted performance (weighted by opponent strength)
    SUM(
      CASE
        WHEN gd.outcome = 'win' THEN 1.0
        WHEN gd.outcome = 'draw' THEN 0.5
        ELSE 0.0
      END * (gd.opponent_elo / 1500)
    ) / NULLIF(SUM(gd.opponent_elo / 1500), 0) as quality_adjusted_score,
    
    -- Expected performance (ELO theory)
    AVG(1.0 / (1.0 + POW(10, (gd.opponent_elo - gd.v7p3r_elo) / 400.0))) as expected_score,
    
    -- Strength of schedule
    AVG(gd.opponent_elo) - 1500 as strength_of_schedule,
    
    -- Time period context
    MIN(gd.date) as first_game_date,
    MAX(gd.date) as last_game_date,
    DATE_DIFF(MAX(gd.date), MIN(gd.date), DAY) as active_days
    
  FROM `chess-engine-metrics-agent.conformed_layer.game_data` gd
  WHERE gd.engine_version IS NOT NULL
  GROUP BY gd.engine_version
  HAVING COUNT(*) >= 50  -- Minimum sample size for statistical significance
),

normalized_metrics AS (
  -- Normalize each metric to 0-100 scale for fair comparison
  SELECT
    engine_version,
    total_games,
    wins,
    losses,
    draws,
    
    -- Raw metrics
    ROUND(game_score, 4) as raw_win_rate,
    ROUND(quality_adjusted_score, 4) as quality_adjusted_win_rate,
    ROUND(expected_score, 4) as expected_win_rate,
    ROUND(game_score - expected_score, 4) as performance_vs_expected,
    
    -- ELO metrics
    ROUND(avg_v7p3r_elo, 1) as avg_elo,
    ROUND(peak_v7p3r_elo, 0) as peak_elo,
    ROUND(avg_opponent_elo, 1) as avg_opponent_elo,
    ROUND(strength_of_schedule, 1) as strength_of_schedule,
    
    -- Time context
    first_game_date,
    last_game_date,
    active_days,
    
    -- Normalized scores (0-100 scale)
    (quality_adjusted_score - MIN(quality_adjusted_score) OVER ()) / 
      NULLIF(MAX(quality_adjusted_score) OVER () - MIN(quality_adjusted_score) OVER (), 0) * 100 
      as quality_score_normalized,
    
    (game_score - expected_score - MIN(game_score - expected_score) OVER ()) /
      NULLIF(MAX(game_score - expected_score) OVER () - MIN(game_score - expected_score) OVER (), 0) * 100
      as performance_score_normalized,
    
    (avg_v7p3r_elo - MIN(avg_v7p3r_elo) OVER ()) /
      NULLIF(MAX(avg_v7p3r_elo) OVER () - MIN(avg_v7p3r_elo) OVER (), 0) * 100
      as elo_score_normalized,
    
    (strength_of_schedule - MIN(strength_of_schedule) OVER ()) /
      NULLIF(MAX(strength_of_schedule) OVER () - MIN(strength_of_schedule) OVER (), 0) * 100
      as schedule_score_normalized
    
  FROM version_metrics
),

composite_rankings AS (
  SELECT
    *,
    
    -- Composite Strength Score (weighted average of normalized metrics)
    ROUND(
      (quality_score_normalized * 0.40) +      -- 40% weight on quality-adjusted performance
      (performance_score_normalized * 0.30) +  -- 30% weight on overperformance
      (elo_score_normalized * 0.20) +         -- 20% weight on ELO rating
      (schedule_score_normalized * 0.10)      -- 10% weight on schedule difficulty
    , 2) as composite_strength_score,
    
    -- Confidence rating (based on sample size and consistency)
    CASE
      WHEN total_games >= 500 AND ABS(performance_vs_expected) < 0.15 THEN 'Very High'
      WHEN total_games >= 200 AND ABS(performance_vs_expected) < 0.20 THEN 'High'
      WHEN total_games >= 100 THEN 'Moderate'
      ELSE 'Low'
    END as confidence_level
    
  FROM normalized_metrics
)

SELECT
  engine_version,
  composite_strength_score,
  
  -- Performance metrics
  quality_adjusted_win_rate,
  performance_vs_expected,
  raw_win_rate,
  expected_win_rate,
  
  -- ELO metrics
  avg_elo,
  peak_elo,
  avg_opponent_elo,
  strength_of_schedule,
  
  -- Sample context
  total_games,
  wins,
  losses,
  draws,
  confidence_level,
  
  -- Time period
  first_game_date,
  last_game_date,
  active_days,
  
  -- Rankings
  RANK() OVER (ORDER BY composite_strength_score DESC) as overall_rank,
  RANK() OVER (ORDER BY quality_adjusted_win_rate DESC) as quality_rank,
  RANK() OVER (ORDER BY performance_vs_expected DESC) as performance_rank,
  RANK() OVER (ORDER BY avg_elo DESC) as elo_rank

FROM composite_rankings
ORDER BY composite_strength_score DESC;

-- ============================================================================
-- HOW TO INTERPRET RESULTS:
-- ============================================================================
-- 
-- composite_strength_score: Overall strength (0-100 scale)
--   - Higher = Stronger version
--   - Accounts for opponent quality, overperformance, ELO, and schedule
--   - Top-ranked version is objectively the strongest
--
-- quality_adjusted_win_rate: Win rate weighted by opponent strength
--   - More reliable than raw win rate
--   - Answers: "How often does this version beat quality opponents?"
--
-- performance_vs_expected: Actual results vs ELO prediction
--   - Positive = Performing better than rating suggests (underrated)
--   - Negative = Performing worse than rating suggests (overrated)
--   - Close to 0 = Rating is accurate
--
-- confidence_level: How much to trust these metrics
--   - Very High = 500+ games with consistent performance
--   - High = 200+ games with reasonable consistency
--   - Moderate/Low = Smaller sample size, less reliable
--
-- ANSWER TO "WHICH VERSION IS STRONGEST?":
-- 1. Look at overall_rank = 1 (highest composite_strength_score)
-- 2. Verify confidence_level is at least "Moderate"
-- 3. Check that it ranks well across multiple metrics (not just one)
-- ============================================================================
