#!/usr/bin/env python3
"""Quick query to view version performance summary"""
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project='chess-engine-metrics-agent')

query = """
SELECT 
  engine_version,
  total_games,
  ROUND(win_rate * 100, 2) as win_rate_pct,
  ROUND(avg_v7p3r_elo, 0) as avg_v7p3r_elo,
  ROUND(avg_opponent_elo, 0) as avg_opponent_elo,
  time_period_start,
  time_period_end
FROM `chess-engine-metrics-agent.reporting_layer.version_performance_summary`
ORDER BY time_period_start
"""

df = client.query(query).to_dataframe()
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
print("\nVersion Performance Summary:")
print("=" * 120)
print(df.to_string(index=False))
print("=" * 120)
print(f"\nTotal versions: {len(df)}")
print(f"Total games: {df['total_games'].sum():,}")
