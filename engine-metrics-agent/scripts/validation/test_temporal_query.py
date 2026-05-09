#!/usr/bin/env python3
"""Test temporal_trends query independently"""
from google.cloud import bigquery

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("Testing temporal_trends SQL...")

# Simplified version - just daily stats first
temporal_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.reporting_layer.temporal_trends` AS
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
ORDER BY date DESC
"""

try:
    print("Executing query...")
    job = client.query(temporal_query)
    job.result()
    
    # Check result
    result = client.query("SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.reporting_layer.temporal_trends`").to_dataframe()
    print(f"✓ Created temporal_trends (daily only): {result['count'].iloc[0]} days")
except Exception as e:
    print(f"✗ Error: {e}")
