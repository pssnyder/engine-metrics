#!/usr/bin/env python3
"""
Analyze Event Field Values for Game Type Classification
"""
from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("=" * 80)
print("EVENT FIELD ANALYSIS - GAME TYPE CATEGORIZATION")
print("=" * 80)

# Get distinct event values and their patterns
# NOTE: game_data is V7P3R-centric (always has opponent field, color field for V7P3R side)
query = """
WITH unique_games AS (
  SELECT 
    game_id,
    event,
    opponent,
    color,
    CASE
      WHEN opponent = 'v7p3r_bot' THEN 'v7p3r_mirror_match'
      WHEN LOWER(event) LIKE '%arena%' OR LOWER(event) LIKE '%local%' OR LOWER(event) LIKE '%tournament%' THEN 'engine_test'
      WHEN event LIKE '%Rated%' THEN 'lichess_rated'
      WHEN event LIKE '%Casual%' THEN 'lichess_casual'
      ELSE 'unknown'
    END as game_category
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY ingested_at DESC) = 1
)
SELECT
  game_category,
  event,
  COUNT(*) as game_count,
  ARRAY_AGG(DISTINCT opponent LIMIT 5) as sample_opponents
FROM unique_games
GROUP BY game_category, event
ORDER BY game_category, game_count DESC
"""

print("\nEvent Values by Game Category:")
print("-" * 80)
result = client.query(query).to_dataframe()
pd.set_option('display.max_colwidth', 60)
print(result.to_string(index=False))

# Get game type breakdown (ALL games are from v7p3r perspective)
query2 = """
WITH unique_games AS (
  SELECT 
    game_id,
    event,
    CASE
      WHEN event LIKE '%Rated%' THEN 'lichess_rated'
      WHEN event LIKE '%Casual%' THEN 'lichess_casual'
      WHEN LOWER(event) LIKE '%arena%' OR LOWER(event) LIKE '%local%' OR LOWER(event) LIKE '%tournament%' THEN 'engine_test'
      ELSE 'unknown'
    END as game_type
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY ingested_at DESC) = 1
)
SELECT
  game_type,
  COUNT(*) as game_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
FROM unique_games
GROUP BY game_type
ORDER BY game_count DESC
"""

print("\n\nGame Type Breakdown (Unique Games Only):")
print("-" * 80)
breakdown = client.query(query2).to_dataframe()
print(breakdown.to_string(index=False))

print("\n" + "=" * 80)
print("\nCLASSIFICATION LOGIC:")
print("  1. Event LIKE '%Rated%'          → game_type='lichess_rated', elo_reliable=TRUE")
print("  2. Event LIKE '%Casual%'         → game_type='lichess_casual', elo_reliable=TRUE")
print("  3. Event LIKE '%arena/local%'    → game_type='engine_test', elo_reliable=FALSE")
print("\nNOTE: game_data is V7P3R-centric. All games have opponent field.")
print("=" * 80)
