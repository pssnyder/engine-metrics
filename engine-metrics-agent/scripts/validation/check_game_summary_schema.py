#!/usr/bin/env python3
"""Check game_summary schema"""
from google.cloud import bigquery

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

table = client.get_table("chess-engine-metrics-agent.conformed_layer.game_summary")

print("=" * 100)
print("GAME_SUMMARY SCHEMA")
print("=" * 100)

for field in table.schema:
    print(f"  {field.name:30} {field.field_type:15} {field.mode:10}")

print(f"\nTotal rows: {table.num_rows:,}")
