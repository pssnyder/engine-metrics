#!/usr/bin/env python3
"""Create temporal_trends table (simplified - daily stats only)"""
from google.cloud import bigquery

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("=" * 100)
print("CREATE TEMPORAL_TRENDS TABLE")
print("=" * 100)

# Simple daily aggregation (skip weekly/monthly for now)
temporal_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.temporal_trends` AS
SELECT
  date as period_date,
  COUNT(*) as games,
  COUNTIF(outcome = 'win') as wins,
  COUNTIF(outcome = 'draw') as draws,
  COUNTIF(outcome = 'loss') as losses,
  ROUND(COUNTIF(outcome = 'win') * 100.0 / COUNT(*), 1) as win_rate,
  ROUND((COUNTIF(outcome = 'win') + 0.5 * COUNTIF(outcome = 'draw')) * 100.0 / COUNT(*), 1) as win_draw_rate,
  ROUND(AVG(v7p3r_elo), 0) as avg_v7p3r_elo,
  ROUND(AVG(opponent_elo), 0) as avg_opponent_elo,
  ROUND(AVG(actual_score) * 100, 1) as actual_score_pct,
  ROUND(AVG(expected_score) * 100, 1) as expected_score_pct,
  ROUND((AVG(actual_score) - AVG(expected_score)) * 100, 1) as performance_vs_expected,
  
  -- Opponent strength distribution
  COUNTIF(relative_opponent_strength = 'stronger') as vs_stronger,
  COUNTIF(relative_opponent_strength = 'equal') as vs_equal,
  COUNTIF(relative_opponent_strength = 'weaker') as vs_weaker
  
FROM `chess-engine-metrics-agent.conformed_layer.game_data`
WHERE is_v7p3r_elo_reliable = TRUE
GROUP BY date
ORDER BY date DESC
"""

try:
    print("Creating table...")
    job = client.query(temporal_query)
    job.result()
    
    result = client.query("SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.reporting_layer.temporal_trends`").to_dataframe()
    print(f"✓ Created temporal_trends: {result['count'].iloc[0]} days")
    print("\n" + "=" * 100)
    print("✓ TEMPORAL_TRENDS CREATED SUCCESSFULLY")
    print("=" * 100)
except Exception as e:
    print(f"✗ Error: {e}")
