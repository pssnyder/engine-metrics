#!/usr/bin/env python3
"""
Analyze Duplicate Ingestion Pattern
"""
from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("=" * 80)
print("DUPLICATE INGESTION PATTERN ANALYSIS")
print("=" * 80)

# Find games with duplicates and their ingestion timestamps
query = """
WITH duplicate_games AS (
  SELECT game_id
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  GROUP BY game_id
  HAVING COUNT(*) > 1
)
SELECT
  d.game_id,
  COUNT(*) as occurrence_count,
  ARRAY_AGG(gd.ingested_at ORDER BY gd.ingested_at) as ingestion_dates,
  MIN(gd.ingested_at) as first_ingested,
  MAX(gd.ingested_at) as last_ingested
FROM duplicate_games d
JOIN `chess-engine-metrics-agent.conformed_layer.game_data` gd
  ON d.game_id = gd.game_id
GROUP BY d.game_id
ORDER BY occurrence_count DESC
LIMIT 10
"""

print("\nTop 10 Most Duplicated Games:")
print("-" * 80)
result = client.query(query).to_dataframe()
print(result.to_string(index=False))

# Get summary statistics
query2 = """
WITH duplicate_games AS (
  SELECT game_id, COUNT(*) as count
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  GROUP BY game_id
  HAVING COUNT(*) > 1
)
SELECT
  MIN(count) as min_duplicates,
  MAX(count) as max_duplicates,
  AVG(count) as avg_duplicates,
  APPROX_QUANTILES(count, 100)[OFFSET(50)] as median_duplicates
FROM duplicate_games
"""

print("\n\nDuplicate Statistics:")
print("-" * 80)
stats = client.query(query2).to_dataframe()
print(stats.to_string(index=False))

print("\n" + "=" * 80)
print("\nRECOMMENDATION:")
print("Keep record with MAX(ingested_at) - most recent data")
print("=" * 80)
