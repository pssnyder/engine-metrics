#!/usr/bin/env python3
"""
Get schema for game_data table
"""
from google.cloud import bigquery

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

table_ref = client.dataset('conformed_layer').table('game_data')
table = client.get_table(table_ref)

print("=" * 80)
print("GAME_DATA SCHEMA")
print("=" * 80)
for field in table.schema:
    print(f"{field.name:30} {field.field_type:15} {field.mode}")
print("=" * 80)
