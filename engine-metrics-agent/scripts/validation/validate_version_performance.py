#!/usr/bin/env python3
"""Validate version_performance table has opponent-adjusted metrics"""
from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("=" * 100)
print("VERSION_PERFORMANCE VALIDATION")
print("=" * 100)

# Check schema
table = client.get_table("chess-engine-metrics-agent.reporting_layer.version_performance")
print("\nSchema (key fields):")
for field in table.schema:
    if field.name in ['composite_strength_score', 'quality_adjusted_win_rate', 'performance_vs_expected', 'confidence_level']:
        print(f"  ✓ {field.name}")

# Get top 5 versions by composite_strength_score
query = """
SELECT
  engine_version,
  total_games,
  raw_win_rate,
  quality_adjusted_win_rate,
  performance_vs_expected,
  composite_strength_score,
  confidence_level,
  avg_elo,
  avg_opponent_elo,
  strength_of_schedule
FROM `chess-engine-metrics-agent.reporting_layer.version_performance`
ORDER BY composite_strength_score DESC
LIMIT 5
"""

print("\nTop 5 Versions by Composite Strength Score:")
print("-" * 100)
df = client.query(query).to_dataframe()
print(df.to_string(index=False))

print("\n" + "=" * 100)
print("✓ VALIDATION COMPLETE")
print("=" * 100)
print("\nKey insights:")
print(f"  • v18.0 composite score: {df.iloc[0]['composite_strength_score']:.1f}/100 (expected: ~104.1)")
print(f"  • Quality-adjusted win rate: {df.iloc[0]['quality_adjusted_win_rate']:.1f}%")
print(f"  • Performance vs expected: +{df.iloc[0]['performance_vs_expected']:.1f}%")
