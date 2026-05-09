#!/usr/bin/env python3
"""Check rebuild progress by listing reporting layer tables"""
from google.cloud import bigquery

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

# List all tables in reporting_layer
tables = client.list_tables("chess-engine-metrics-agent.reporting_layer")

print("=" * 80)
print("REPORTING LAYER TABLES")
print("=" * 80)

table_count = 0
for table in tables:
    table_ref = f"{table.project}.{table.dataset_id}.{table.table_id}"
    table_obj = client.get_table(table_ref)
    print(f"✓ {table.table_id}: {table_obj.num_rows:,} rows")
    table_count += 1

print(f"\nTotal tables: {table_count}/7")

if table_count == 7:
    print("✓ ALL 7 TABLES CREATED!")
elif table_count < 7:
    print(f"⏳ Rebuild in progress... ({table_count}/7 completed)")
else:
    print("⚠️  More than 7 tables found (unexpected)")
