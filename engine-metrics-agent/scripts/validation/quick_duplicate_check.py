#!/usr/bin/env python3
"""
Quick Duplicate Detection - Run First
"""
from google.cloud import bigquery

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("=" * 80)
print("DUPLICATE DETECTION - CONFORMED LAYER")
print("=" * 80)

# Check game_data for duplicates
query = """
SELECT
  COUNT(DISTINCT game_id) as unique_games,
  COUNT(*) as total_records,
  COUNT(*) - COUNT(DISTINCT game_id) as duplicate_records
FROM `chess-engine-metrics-agent.conformed_layer.game_data`
"""

result = client.query(query).to_dataframe()
print("\nGame Data Table:")
print(result.to_string(index=False))

unique_games = result['unique_games'].iloc[0]
total_records = result['total_records'].iloc[0]
duplicates = result['duplicate_records'].iloc[0]

if duplicates > 0:
    pct = (duplicates / total_records) * 100
    print(f"\n⚠️  WARNING: {duplicates:,} duplicate records ({pct:.1f}% of total)")
    print(f"   Unique games: {unique_games:,}")
    print(f"   Total records: {total_records:,}")
    print(f"   Metrics are inflated by {pct:.1f}%!")
else:
    print(f"\n✅ No duplicates found - {unique_games:,} unique games")

print("\n" + "=" * 80)
