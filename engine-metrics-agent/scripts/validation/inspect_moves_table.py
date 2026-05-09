#!/usr/bin/env python3
"""
Inspect current moves table to determine what data we have
"""
from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

pd.set_option('display.max_colwidth', 80)

print("=" * 100)
print("MOVES TABLE INSPECTION")
print("=" * 100)

# Get schema
print("\n[1/4] Schema:")
print("-" * 100)
table = client.get_table("chess-engine-metrics-agent.conformed_layer.moves")
for field in table.schema:
    print(f"  {field.name:20} {field.field_type:15} {field.mode}")

# Get summary stats
print("\n[2/4] Summary Statistics:")
print("-" * 100)
stats_query = """
SELECT
  COUNT(*) as total_moves,
  COUNT(DISTINCT game_id) as unique_games,
  ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT game_id), 1) as avg_moves_per_game,
  MIN(move_number) as min_move,
  MAX(move_number) as max_move,
  
  -- Tactical move distribution
  COUNTIF(is_capture = TRUE) as captures,
  COUNTIF(is_check = TRUE) as checks,
  COUNTIF(is_castle = TRUE) as castles,
  
  -- Game phase distribution
  COUNTIF(game_phase = 'opening') as opening_moves,
  COUNTIF(game_phase = 'middlegame') as middlegame_moves,
  COUNTIF(game_phase = 'endgame') as endgame_moves,
  
  -- Data completeness
  COUNTIF(material_balance IS NOT NULL) as has_material_data,
  COUNTIF(clock IS NOT NULL) as has_clock_data
FROM `chess-engine-metrics-agent.conformed_layer.moves`
"""
stats = client.query(stats_query).to_dataframe()
print(stats.to_string(index=False))

# Sample moves to see data structure
print("\n[3/4] Sample Move Records (10 random):")
print("-" * 100)
sample_query = """
SELECT
  game_id,
  move_number,
  color,
  san,
  piece,
  is_capture,
  is_check,
  material_balance,
  game_phase,
  clock
FROM `chess-engine-metrics-agent.conformed_layer.moves`
ORDER BY RAND()
LIMIT 10
"""
samples = client.query(sample_query).to_dataframe()
print(samples.to_string(index=False))

# Check for deduplication needs
print("\n[4/4] Deduplication Check:")
print("-" * 100)
dup_query = """
WITH duplicates AS (
  SELECT game_id, move_number, color, COUNT(*) as dup_count
  FROM `chess-engine-metrics-agent.conformed_layer.moves`
  GROUP BY game_id, move_number, color
  HAVING COUNT(*) > 1
)
SELECT COUNT(*) as duplicate_move_records
FROM duplicates
"""
dups = client.query(dup_query).to_dataframe()
print(dups.to_string(index=False))

if dups['duplicate_move_records'].iloc[0] > 0:
    print(f"\n⚠️  Found {dups['duplicate_move_records'].iloc[0]} duplicate move records!")
else:
    print("\n✓ No duplicate move records found")

print("\n" + "=" * 100)
print("CONCLUSION:")
print("=" * 100)
print("\nNext steps depend on findings:")
print("  1. If moves have evals → Extract from comments (Phase 2)")
print("  2. If no evals → Run Stockfish batch analysis (Phase 3)")
print("=" * 100)
