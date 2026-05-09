-- ============================================================================
-- OPPONENT-ADJUSTED PERFORMANCE ANALYSIS
-- ============================================================================
-- Purpose: Calculate opponent-strength-weighted performance metrics
-- Author: ETL Validation Framework
-- Date: 2026-05-03
--
-- This addresses the scenario where:
-- - Engine A plays 100 games vs weak opponents (1200 ELO) with 90% win rate
-- - Engine B plays 20 games vs strong opponents (1800 ELO) with 60% win rate
-- - Raw metrics would favor Engine A, but Engine B is actually stronger
--
-- Metrics calculated:
-- 1. Quality-Adjusted Win Rate (weighted by opponent strength)
-- 2. Expected Performance Rating (EPR) based on ELO differences
-- 3. Performance vs Expected (overperformance/underperformance)
-- 4. Strength of Schedule (average opponent ELO)
-- ============================================================================

WITH version_games AS (
  -- Get all games with outcome and opponent strength
  SELECT
    gd.engine_version,
    gd.outcome,
    gd.v7p3r_elo,
    gd.opponent_elo,
    gd.opponent_elo - 1500 as opponent_strength_factor, -- Relative to baseline
    CASE
      WHEN gd.outcome = 'win' THEN 1.0
      WHEN gd.outcome = 'draw' THEN 0.5
      ELSE 0.0
    END as game_score
  FROM `chess-engine-metrics-agent.conformed_layer.game_data` gd
  WHERE gd.engine_version IS NOT NULL
),

version_performance AS (
  SELECT
    engine_version,
    COUNT(*) as total_games,
    
    -- Raw metrics
    AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END) as raw_win_rate,
    AVG(game_score) as raw_score_rate,
    
    -- Opponent strength context
    AVG(opponent_elo) as avg_opponent_elo,
    STDDEV(opponent_elo) as opponent_elo_stddev,
    MIN(opponent_elo) as min_opponent_elo,
    MAX(opponent_elo) as max_opponent_elo,
    
    -- Quality-adjusted metrics (weight by opponent strength)
    SUM(game_score * (opponent_elo / 1500)) / SUM(opponent_elo / 1500) as quality_adjusted_win_rate,
    
    -- Expected performance (based on ELO theory)
    -- Expected score = 1 / (1 + 10^((opponent_elo - v7p3r_elo)/400))
    AVG(1.0 / (1.0 + POW(10, (opponent_elo - v7p3r_elo) / 400.0))) as expected_score,
    
    -- Actual vs Expected
    AVG(game_score) - AVG(1.0 / (1.0 + POW(10, (opponent_elo - v7p3r_elo) / 400.0))) as performance_vs_expected,
    
    -- Difficulty rating (how hard was the schedule)
    AVG(opponent_strength_factor) as strength_of_schedule
    
  FROM version_games
  GROUP BY engine_version
)

SELECT
  engine_version,
  total_games,
  
  -- Raw metrics
  ROUND(raw_win_rate, 4) as raw_win_rate,
  ROUND(raw_score_rate, 4) as raw_score_rate,
  
  -- Opponent context
  ROUND(avg_opponent_elo, 1) as avg_opponent_elo,
  ROUND(opponent_elo_stddev, 1) as opponent_elo_range,
  ROUND(min_opponent_elo, 0) as weakest_opponent,
  ROUND(max_opponent_elo, 0) as strongest_opponent,
  
  -- Adjusted metrics (THE KEY INDICATORS)
  ROUND(quality_adjusted_win_rate, 4) as quality_adjusted_win_rate,
  ROUND(expected_score, 4) as expected_score,
  ROUND(performance_vs_expected, 4) as performance_vs_expected,
  
  -- Performance rating
  CASE
    WHEN performance_vs_expected > 0.10 THEN 'Overperforming'
    WHEN performance_vs_expected < -0.10 THEN 'Underperforming'
    ELSE 'As Expected'
  END as performance_category,
  
  -- Strength of schedule
  ROUND(strength_of_schedule, 1) as strength_of_schedule,
  CASE
    WHEN strength_of_schedule > 100 THEN 'Very Hard'
    WHEN strength_of_schedule > 0 THEN 'Hard'
    WHEN strength_of_schedule > -100 THEN 'Easy'
    ELSE 'Very Easy'
  END as schedule_difficulty

FROM version_performance
WHERE total_games >= 10  -- Filter out versions with insufficient data
ORDER BY quality_adjusted_win_rate DESC;

-- ============================================================================
-- INTERPRETATION GUIDE:
-- ============================================================================
-- 
-- raw_win_rate: Simple wins/total_games (can be misleading)
-- quality_adjusted_win_rate: Weighted by opponent strength (more accurate)
-- expected_score: What ELO theory predicts based on rating difference
-- performance_vs_expected: How much better/worse than ELO prediction
--   > +0.10 = Significantly overperforming (stronger than rating suggests)
--   > -0.10 = Significantly underperforming (weaker than rating suggests)
-- 
-- strength_of_schedule: Average difficulty of opponents faced
--   > +100 = Faced opponents 100+ ELO stronger than baseline
--   > -100 = Faced opponents 100+ ELO weaker than baseline
-- 
-- TO COMPARE VERSIONS:
-- 1. Look at quality_adjusted_win_rate first (not raw_win_rate)
-- 2. Consider performance_vs_expected (overperformers are stronger)
-- 3. Account for schedule_difficulty (harder schedule = more impressive)
-- ============================================================================
