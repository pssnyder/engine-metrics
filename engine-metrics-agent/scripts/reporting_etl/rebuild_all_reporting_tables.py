#!/usr/bin/env python3
"""
Rebuild All Reporting Tables with Opponent-Adjusted Metrics

This script deletes and rebuilds all 7 Tier 1 reporting tables:
1. version_performance - Engine version strength with composite scoring
2. opponent_strength - Performance by opponent ELO brackets
3. opening_performance - Repertoire effectiveness analysis
4. time_control_performance - Performance by time format
5. temporal_trends - Performance over time periods
6. castling_analysis - Castling pattern effectiveness
7. queen_trade_analysis - Queen trade pattern effectiveness

All tables now use:
- Deduplicated game_data (5,069 unique games)
- Quality-adjusted win rates (weighted by opponent strength)
- Performance vs expected score (ELO theory)
- Composite strength scores
"""
from google.cloud import bigquery
import time

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("=" * 100)
print("REBUILD ALL REPORTING TABLES WITH OPPONENT-ADJUSTED METRICS")
print("=" * 100)

# Step 1: Delete all existing reporting tables
print("\n[1/8] Deleting old reporting tables...")
print("-" * 100)

reporting_tables = [
    "version_performance",
    "opponent_strength",
    "opening_performance",
    "time_control_performance",
    "temporal_trends",
    "castling_analysis",
    "queen_trade_analysis"
]

for table_name in reporting_tables:
    try:
        client.delete_table(f"chess-engine-metrics-agent.reporting_layer.{table_name}", not_found_ok=True)
        print(f"✓ Deleted: {table_name}")
    except Exception as e:
        print(f"⚠️  Could not delete {table_name}: {e}")

# Step 2: Rebuild version_performance with composite scoring
print("\n[2/8] Rebuilding: version_performance (with composite strength scoring)...")
print("-" * 100)

version_perf_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.version_performance` AS
WITH version_stats AS (
  SELECT
    engine_version,
    COUNT(*) as total_games,
    
    -- Basic metrics
    COUNTIF(outcome = 'win') as wins,
    COUNTIF(outcome = 'draw') as draws,
    COUNTIF(outcome = 'loss') as losses,
    ROUND(COUNTIF(outcome = 'win') * 100.0 / COUNT(*), 1) as raw_win_rate,
    ROUND((COUNTIF(outcome = 'win') + 0.5 * COUNTIF(outcome = 'draw')) * 100.0 / COUNT(*), 1) as win_draw_rate,
    
    -- ELO metrics
    ROUND(AVG(v7p3r_elo), 0) as avg_elo,
    ROUND(AVG(opponent_elo), 0) as avg_opponent_elo,
    ROUND(AVG(opponent_elo - v7p3r_elo), 0) as avg_elo_diff,
    MIN(v7p3r_elo) as min_elo,
    MAX(v7p3r_elo) as max_elo,
    
    -- Opponent strength distribution
    COUNTIF(relative_opponent_strength = 'stronger') as vs_stronger,
    COUNTIF(relative_opponent_strength = 'equal') as vs_equal,
    COUNTIF(relative_opponent_strength = 'weaker') as vs_weaker,
    
    -- Quality-adjusted win rate (weighted by opponent strength)
    ROUND(
      SUM(
        CASE
          WHEN outcome = 'win' AND relative_opponent_strength = 'stronger' THEN 1.5
          WHEN outcome = 'win' AND relative_opponent_strength = 'equal' THEN 1.0
          WHEN outcome = 'win' AND relative_opponent_strength = 'weaker' THEN 0.75
          WHEN outcome = 'draw' AND relative_opponent_strength = 'stronger' THEN 0.75
          WHEN outcome = 'draw' AND relative_opponent_strength = 'equal' THEN 0.5
          WHEN outcome = 'draw' AND relative_opponent_strength = 'weaker' THEN 0.375
          ELSE 0
        END
      ) * 100.0 / COUNT(*),
      1
    ) as quality_adjusted_win_rate,
    
    -- Performance vs expected (ELO theory)
    ROUND(AVG(expected_score) * 100, 1) as expected_score_pct,
    ROUND(AVG(actual_score) * 100, 1) as actual_score_pct,
    ROUND((AVG(actual_score) - AVG(expected_score)) * 100, 1) as performance_vs_expected,
    
    -- Schedule difficulty
    CASE
      WHEN AVG(opponent_elo) >= 1600 THEN 'very_hard'
      WHEN AVG(opponent_elo) >= 1500 THEN 'hard'
      WHEN AVG(opponent_elo) >= 1400 THEN 'moderate'
      ELSE 'easy'
    END as strength_of_schedule,
    
    -- Time-based metrics
    COUNTIF(termination = 'Time forfeit') as time_forfeits,
    ROUND(COUNTIF(termination = 'Time forfeit') * 100.0 / COUNT(*), 1) as time_forfeit_rate,
    
    -- Date range
    MIN(date) as first_game_date,
    MAX(date) as last_game_date,
    DATE_DIFF(MAX(date), MIN(date), DAY) as days_active
    
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  WHERE engine_version IS NOT NULL
    AND is_v7p3r_elo_reliable = TRUE
  GROUP BY engine_version
)
SELECT
  *,
  
  -- Composite Strength Score (0-100+)
  ROUND(
    (quality_adjusted_win_rate * 0.4) +
    ((performance_vs_expected + 20) * 1.5) +
    ((avg_elo - 1200) / 10) +
    (CASE strength_of_schedule
      WHEN 'very_hard' THEN 10
      WHEN 'hard' THEN 7
      WHEN 'moderate' THEN 4
      ELSE 0
    END),
    1
  ) as composite_strength_score,
  
  -- Sample size confidence
  CASE
    WHEN total_games >= 500 THEN 'very_high'
    WHEN total_games >= 200 THEN 'high'
    WHEN total_games >= 100 THEN 'medium'
    WHEN total_games >= 50 THEN 'low'
    ELSE 'very_low'
  END as confidence_level
  
FROM version_stats
ORDER BY composite_strength_score DESC
"""

job = client.query(version_perf_query)
job.result()
result = client.query("SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.reporting_layer.version_performance`").to_dataframe()
print(f"✓ Created version_performance: {result['count'].iloc[0]} versions")

time.sleep(2)

# Step 3: Rebuild opponent_strength
print("\n[3/8] Rebuilding: opponent_strength...")
print("-" * 100)

opponent_strength_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.opponent_strength` AS
WITH elo_brackets AS (
  SELECT
    CASE
      WHEN opponent_elo < 1400 THEN '<1400'
      WHEN opponent_elo < 1600 THEN '1400-1600'
      WHEN opponent_elo < 1800 THEN '1600-1800'
      WHEN opponent_elo < 2000 THEN '1800-2000'
      WHEN opponent_elo < 2200 THEN '2000-2200'
      ELSE '2200+'
    END as elo_bracket,
    *
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  WHERE opponent_elo IS NOT NULL
    AND is_opponent_elo_reliable = TRUE
)
SELECT
  elo_bracket,
  COUNT(*) as total_games,
  COUNTIF(outcome = 'win') as wins,
  COUNTIF(outcome = 'draw') as draws,
  COUNTIF(outcome = 'loss') as losses,
  ROUND(COUNTIF(outcome = 'win') * 100.0 / COUNT(*), 1) as win_rate,
  ROUND((COUNTIF(outcome = 'win') + 0.5 * COUNTIF(outcome = 'draw')) * 100.0 / COUNT(*), 1) as win_draw_rate,
  ROUND(AVG(v7p3r_elo), 0) as avg_v7p3r_elo,
  ROUND(AVG(opponent_elo), 0) as avg_opponent_elo,
  ROUND(AVG(actual_score) * 100, 1) as actual_score_pct,
  ROUND(AVG(expected_score) * 100, 1) as expected_score_pct,
  ROUND((AVG(actual_score) - AVG(expected_score)) * 100, 1) as performance_vs_expected
FROM elo_brackets
GROUP BY elo_bracket
ORDER BY 
  CASE elo_bracket
    WHEN '<1400' THEN 1
    WHEN '1400-1600' THEN 2
    WHEN '1600-1800' THEN 3
    WHEN '1800-2000' THEN 4
    WHEN '2000-2200' THEN 5
    WHEN '2200+' THEN 6
  END
"""

job = client.query(opponent_strength_query)
job.result()
result = client.query("SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.reporting_layer.opponent_strength`").to_dataframe()
print(f"✓ Created opponent_strength: {result['count'].iloc[0]} ELO brackets")

time.sleep(2)

# Step 4: Rebuild opening_performance
print("\n[4/8] Rebuilding: opening_performance...")
print("-" * 100)

opening_perf_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.opening_performance` AS
WITH opening_family AS (
  SELECT
    SUBSTR(g.eco, 1, 1) as eco_category,
    SPLIT(g.opening, ':')[OFFSET(0)] as opening_family,
    g.game_id,
    g.outcome,
    g.color,
    g.actual_score,
    g.expected_score,
    g.opponent_elo,
    g.is_v7p3r_elo_reliable,
    gs.v7p3r_castled
  FROM `chess-engine-metrics-agent.conformed_layer.game_data` g
  JOIN `chess-engine-metrics-agent.conformed_layer.game_summary` gs USING (game_id)
  WHERE g.opening IS NOT NULL
)
SELECT
  eco_category,
  opening_family,
  COUNT(*) as total_games,
  COUNTIF(outcome = 'win') as wins,
  COUNTIF(outcome = 'draw') as draws,
  COUNTIF(outcome = 'loss') as losses,
  ROUND(COUNTIF(outcome = 'win') * 100.0 / COUNT(*), 1) as win_rate,
  
  -- Color preference
  COUNTIF(color = 'white') as games_as_white,
  COUNTIF(color = 'black') as games_as_black,
  CASE
    WHEN COUNTIF(color = 'white') > COUNTIF(color = 'black') THEN 'white'
    WHEN COUNTIF(color = 'black') > COUNTIF(color = 'white') THEN 'black'
    ELSE 'balanced'
  END as preferred_color,
  
  -- Performance metrics
  ROUND(AVG(actual_score) * 100, 1) as actual_score_pct,
  ROUND(AVG(expected_score) * 100, 1) as expected_score_pct,
  ROUND((AVG(actual_score) - AVG(expected_score)) * 100, 1) as performance_vs_expected,
  
  -- Castling preference
  APPROX_TOP_COUNT(v7p3r_castled, 1)[OFFSET(0)].value as most_common_castle,
  
  -- Sample strength
  ROUND(AVG(opponent_elo), 0) as avg_opponent_elo
  
FROM opening_family
WHERE is_v7p3r_elo_reliable = TRUE
GROUP BY eco_category, opening_family
HAVING total_games >= 5
ORDER BY total_games DESC
"""

job = client.query(opening_perf_query)
job.result()
result = client.query("SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.reporting_layer.opening_performance`").to_dataframe()
print(f"✓ Created opening_performance: {result['count'].iloc[0]} opening families")

time.sleep(2)

# Step 5: Rebuild time_control_performance
print("\n[5/8] Rebuilding: time_control_performance...")
print("-" * 100)

time_control_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.time_control_performance` AS
WITH time_categories AS (
  SELECT
    CASE
      WHEN SAFE_CAST(SPLIT(time_control, '+')[OFFSET(0)] AS INT64) < 180 THEN 'bullet'
      WHEN SAFE_CAST(SPLIT(time_control, '+')[OFFSET(0)] AS INT64) < 480 THEN 'blitz'
      WHEN SAFE_CAST(SPLIT(time_control, '+')[OFFSET(0)] AS INT64) < 1500 THEN 'rapid'
      ELSE 'classical'
    END as time_category,
    *
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  WHERE time_control IS NOT NULL
)
SELECT
  time_category,
  COUNT(*) as total_games,
  COUNTIF(outcome = 'win') as wins,
  COUNTIF(outcome = 'draw') as draws,
  COUNTIF(outcome = 'loss') as losses,
  ROUND(COUNTIF(outcome = 'win') * 100.0 / COUNT(*), 1) as win_rate,
  
  -- Quality-adjusted metrics
  ROUND(AVG(actual_score) * 100, 1) as actual_score_pct,
  ROUND(AVG(expected_score) * 100, 1) as expected_score_pct,
  ROUND((AVG(actual_score) - AVG(expected_score)) * 100, 1) as performance_vs_expected,
  
  -- Time management
  COUNTIF(termination = 'Time forfeit') as time_forfeits,
  ROUND(COUNTIF(termination = 'Time forfeit') * 100.0 / COUNT(*), 1) as time_forfeit_rate,
  
  -- Strength metrics
  ROUND(AVG(v7p3r_elo), 0) as avg_v7p3r_elo,
  ROUND(AVG(opponent_elo), 0) as avg_opponent_elo
  
FROM time_categories
WHERE is_v7p3r_elo_reliable = TRUE
GROUP BY time_category
ORDER BY 
  CASE time_category
    WHEN 'bullet' THEN 1
    WHEN 'blitz' THEN 2
    WHEN 'rapid' THEN 3
    WHEN 'classical' THEN 4
  END
"""

job = client.query(time_control_query)
job.result()
result = client.query("SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.reporting_layer.time_control_performance`").to_dataframe()
print(f"✓ Created time_control_performance: {result['count'].iloc[0]} time formats")

time.sleep(2)

# Step 6: Rebuild temporal_trends
print("\n[6/8] Rebuilding: temporal_trends...")
print("-" * 100)

temporal_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.temporal_trends` AS
WITH daily_stats AS (
  SELECT
    date as period_start,
    date as period_end,
    'daily' as period_type,
    COUNT(*) as games,
    COUNTIF(outcome = 'win') as wins,
    ROUND(AVG(v7p3r_elo), 0) as avg_elo,
    ROUND(AVG(actual_score) * 100, 1) as performance
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  WHERE is_v7p3r_elo_reliable = TRUE
  GROUP BY date
),
weekly_stats AS (
  SELECT
    DATE_TRUNC(date, WEEK) as period_start,
    DATE_ADD(DATE_TRUNC(date, WEEK), INTERVAL 6 DAY) as period_end,
    'weekly' as period_type,
    COUNT(*) as games,
    COUNTIF(outcome = 'win') as wins,
    ROUND(AVG(v7p3r_elo), 0) as avg_elo,
    ROUND(AVG(actual_score) * 100, 1) as performance
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  WHERE is_v7p3r_elo_reliable = TRUE
  GROUP BY DATE_TRUNC(date, WEEK)
),
monthly_stats AS (
  SELECT
    DATE_TRUNC(date, MONTH) as period_start,
    LAST_DAY(date) as period_end,
    'monthly' as period_type,
    COUNT(*) as games,
    COUNTIF(outcome = 'win') as wins,
    ROUND(AVG(v7p3r_elo), 0) as avg_elo,
    ROUND(AVG(actual_score) * 100, 1) as performance
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  WHERE is_v7p3r_elo_reliable = TRUE
  GROUP BY DATE_TRUNC(date, MONTH)
)
SELECT * FROM daily_stats
UNION ALL
SELECT * FROM weekly_stats
UNION ALL
SELECT * FROM monthly_stats
ORDER BY period_type, period_start DESC
"""

job = client.query(temporal_query)
job.result()
result = client.query("SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.reporting_layer.temporal_trends`").to_dataframe()
print(f"✓ Created temporal_trends: {result['count'].iloc[0]} periods")

time.sleep(2)

# Step 7: Rebuild castling_analysis
print("\n[7/8] Rebuilding: castling_analysis...")
print("-" * 100)

castling_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.castling_analysis` AS
WITH castling_patterns AS (
  SELECT
    CONCAT(
      COALESCE(g.color, 'unknown'), '_',
      COALESCE(gs.v7p3r_castled, 'none'), '_vs_',
      COALESCE(gs.opponent_castled, 'none')
    ) as castling_pattern,
    g.*,
    gs.v7p3r_castled,
    gs.opponent_castled,
    gs.queen_traded
  FROM `chess-engine-metrics-agent.conformed_layer.game_data` g
  JOIN `chess-engine-metrics-agent.conformed_layer.game_summary` gs ON g.game_id = gs.game_id
  WHERE g.is_v7p3r_elo_reliable = TRUE
)
SELECT
  castling_pattern,
  COUNT(*) as total_games,
  COUNTIF(outcome = 'win') as wins,
  COUNTIF(outcome = 'draw') as draws,
  COUNTIF(outcome = 'loss') as losses,
  ROUND(COUNTIF(outcome = 'win') * 100.0 / COUNT(*), 1) as win_rate,
  
  -- Performance metrics
  ROUND(AVG(actual_score) * 100, 1) as actual_score_pct,
  ROUND(AVG(expected_score) * 100, 1) as expected_score_pct,
  ROUND((AVG(actual_score) - AVG(expected_score)) * 100, 1) as performance_vs_expected,
  
  -- Queen trade correlation
  COUNTIF(queen_traded = TRUE) as games_with_queen_trade,
  ROUND(COUNTIF(queen_traded = TRUE) * 100.0 / COUNT(*), 1) as queen_trade_rate
  
FROM castling_patterns
GROUP BY castling_pattern
HAVING total_games >= 10
ORDER BY total_games DESC
"""

job = client.query(castling_query)
job.result()
result = client.query("SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.reporting_layer.castling_analysis`").to_dataframe()
print(f"✓ Created castling_analysis: {result['count'].iloc[0]} patterns")

time.sleep(2)

# Step 8: Rebuild queen_trade_analysis
print("\n[8/8] Rebuilding: queen_trade_analysis...")
print("-" * 100)

queen_trade_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.queen_trade_analysis` AS
WITH queen_trades AS (
  SELECT
    g.*,
    gs.queen_traded,
    CASE
      WHEN gs.queen_trade_move IS NULL THEN 'not_traded'
      WHEN gs.queen_trade_move <= 20 THEN 'early_trade'
      WHEN gs.queen_trade_move <= 40 THEN 'mid_trade'
      ELSE 'late_trade'
    END as trade_timing
  FROM `chess-engine-metrics-agent.conformed_layer.game_data` g
  JOIN `chess-engine-metrics-agent.conformed_layer.game_summary` gs ON g.game_id = gs.game_id
  WHERE g.is_v7p3r_elo_reliable = TRUE
)
SELECT
  trade_timing,
  COUNT(*) as total_games,
  COUNTIF(outcome = 'win') as wins,
  COUNTIF(outcome = 'draw') as draws,
  COUNTIF(outcome = 'loss') as losses,
  ROUND(COUNTIF(outcome = 'win') * 100.0 / COUNT(*), 1) as win_rate,
  
  -- Performance metrics
  ROUND(AVG(actual_score) * 100, 1) as actual_score_pct,
  ROUND(AVG(expected_score) * 100, 1) as expected_score_pct,
  ROUND((AVG(actual_score) - AVG(expected_score)) * 100, 1) as performance_vs_expected,
  
  -- Context
  ROUND(AVG(v7p3r_elo), 0) as avg_v7p3r_elo,
  ROUND(AVG(opponent_elo), 0) as avg_opponent_elo,
  
  -- Opening correlation
  PARSE_JSON(TO_JSON_STRING(APPROX_TOP_COUNT(SPLIT(opening, ':')[OFFSET(0)], 3))) as top_openings
  
FROM queen_trades
GROUP BY trade_timing
ORDER BY 
  CASE trade_timing
    WHEN 'early_trade' THEN 1
    WHEN 'mid_trade' THEN 2
    WHEN 'late_trade' THEN 3
    WHEN 'not_traded' THEN 4
  END
"""

job = client.query(queen_trade_query)
job.result()
result = client.query("SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.reporting_layer.queen_trade_analysis`").to_dataframe()
print(f"✓ Created queen_trade_analysis: {result['count'].iloc[0]} trade patterns")

print("\n" + "=" * 100)
print("✓ ALL REPORTING TABLES REBUILT SUCCESSFULLY")
print("=" * 100)

# Final summary
print("\nReporting Layer Summary:")
print("-" * 100)
summary_query = """
SELECT
  table_name,
  row_count,
  ROUND(size_bytes / 1024 / 1024, 2) as size_mb
FROM `chess-engine-metrics-agent.reporting_layer.__TABLES__`
ORDER BY table_name
"""
summary = client.query(summary_query).to_dataframe()
print(summary.to_string(index=False))

print("\n" + "=" * 100)
print("Next steps:")
print("  1. Validate accuracy of reporting tables")
print("  2. Run sample queries to verify opponent-adjusted metrics")
print("  3. Export to CSV for analysis/visualization")
print("=" * 100)
