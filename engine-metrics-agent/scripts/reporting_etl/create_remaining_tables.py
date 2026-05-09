#!/usr/bin/env python3
"""Create castling_analysis and queen_trade_analysis tables (skip temporal_trends for now)"""
from google.cloud import bigquery
import time

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("=" * 100)
print("REBUILD REMAINING REPORTING TABLES")
print("=" * 100)

# Step 1: Rebuild castling_analysis
print("\n[1/2] Rebuilding: castling_analysis...")
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
    g.outcome,
    g.actual_score,
    g.expected_score,
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

# Step 2: Rebuild queen_trade_analysis
print("\n[2/2] Rebuilding: queen_trade_analysis...")
print("-" * 100)

queen_trade_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.queen_trade_analysis` AS
WITH queen_trades AS (
  SELECT
    g.game_id,
    g.outcome,
    g.actual_score,
    g.expected_score,
    g.v7p3r_elo,
    g.opponent_elo,
    g.opening,
    gs.queen_traded,
    CASE
      WHEN gs.queen_traded_move IS NULL THEN 'not_traded'
      WHEN gs.queen_traded_move <= 20 THEN 'early_trade'
      WHEN gs.queen_traded_move <= 40 THEN 'mid_trade'
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
  ROUND(AVG(opponent_elo), 0) as avg_opponent_elo
  
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
print("✓ REMAINING TABLES CREATED SUCCESSFULLY")
print("=" * 100)
print("\nNote: temporal_trends skipped due to SQL complexity - will create separately")
