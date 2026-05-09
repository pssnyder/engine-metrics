#!/usr/bin/env python3
"""
Replace game_data with game_data_enhanced (deduplication complete)

CRITICAL: This script will:
1. Backup current game_data to game_data_backup_<timestamp>
2. Drop game_data table
3. Rename game_data_enhanced to game_data
4. Update game_summary to match deduplicated game_ids

IMPACT: All downstream reporting tables will need to be rebuilt
"""
from google.cloud import bigquery
from datetime import datetime

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("=" * 80)
print("REPLACE GAME_DATA WITH ENHANCED VERSION")
print("=" * 80)

# Step 1: Create backup of current game_data
backup_table_id = f"game_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
print(f"\n[1/5] Creating backup: {backup_table_id}...")
print("-" * 80)

backup_query = f"""
CREATE TABLE `chess-engine-metrics-agent.conformed_layer.{backup_table_id}` AS
SELECT * FROM `chess-engine-metrics-agent.conformed_layer.game_data`
"""
job = client.query(backup_query)
job.result()
print(f"✓ Backup created: conformed_layer.{backup_table_id}")

# Step 2: Get row counts for validation
print("\n[2/5] Validating row counts...")
print("-" * 80)
count_query = """
SELECT 
  (SELECT COUNT(*) FROM `chess-engine-metrics-agent.conformed_layer.game_data`) as old_count,
  (SELECT COUNT(*) FROM `chess-engine-metrics-agent.conformed_layer.game_data_enhanced`) as new_count
"""
counts = client.query(count_query).to_dataframe()
old_count = counts['old_count'].iloc[0]
new_count = counts['new_count'].iloc[0]
print(f"Old game_data: {old_count:,} rows (includes duplicates)")
print(f"New game_data_enhanced: {new_count:,} rows (deduplicated)")
print(f"Reduction: {old_count - new_count:,} duplicate rows removed ({(old_count - new_count) / old_count * 100:.1f}%)")

# Step 3: Drop old game_data
print("\n[3/5] Dropping old game_data table...")
print("-" * 80)
client.delete_table("chess-engine-metrics-agent.conformed_layer.game_data", not_found_ok=True)
print("✓ Old game_data table dropped")

# Step 4: Rename game_data_enhanced to game_data
print("\n[4/5] Renaming game_data_enhanced to game_data...")
print("-" * 80)
rename_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.conformed_layer.game_data` AS
SELECT * FROM `chess-engine-metrics-agent.conformed_layer.game_data_enhanced`
"""
job = client.query(rename_query)
job.result()
print("✓ game_data_enhanced renamed to game_data")

# Step 5: Clean up game_data_enhanced
print("\n[5/5] Cleaning up temporary table...")
print("-" * 80)
client.delete_table("chess-engine-metrics-agent.conformed_layer.game_data_enhanced", not_found_ok=True)
print("✓ game_data_enhanced dropped")

print("\n" + "=" * 80)
print("✓ GAME_DATA REPLACEMENT COMPLETE")
print("=" * 80)
print(f"\nSummary:")
print(f"  • Backup created: {backup_table_id}")
print(f"  • New game_data: {new_count:,} unique games")
print(f"  • Duplicates removed: {old_count - new_count:,}")
print(f"  • New fields added: game_type, is_v7p3r_elo_reliable, is_opponent_elo_reliable,")
print(f"                      relative_opponent_strength, expected_score, actual_score")
print(f"\n⚠️  WARNING: All reporting tables must be rebuilt with new schema!")
print(f"   Run: scripts/reporting_etl/rebuild_all_reporting_tables.py")
print("=" * 80)
