#!/usr/bin/env python3
"""
Phase 2: Deduplicate and Enhance Conformed Layer

This script will:
1. Deduplicate game_data (keep most recent ingested_at)
2. Add game_type, elo_reliability flags, opponent strength fields
3. Create new enhanced game_data table

Based on findings:
- 72.4% duplicates (13,267 of 18,336 records)
- 5,069 unique games
- Event field uses lowercase ("rated blitz game", not "Rated")
"""
from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

print("=" * 80)
print("PHASE 2: DEDUPLICATE & ENHANCE CONFORMED LAYER")
print("=" * 80)

# Step 1: Create enhanced game_data table with deduplication
create_enhanced_query = """
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.conformed_layer.game_data_enhanced` AS
WITH deduplicated AS (
  -- Keep only most recent record for each game_id
  SELECT *
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY ingested_at DESC) = 1
),
enhanced AS (
  SELECT
    -- Original columns
    game_id,
    date,
    time,
    engine_version,
    event,
    color,
    outcome,
    result,
    v7p3r_elo,
    opponent,
    opponent_elo,
    rating_diff,
    time_control,
    eco,
    opening,
    termination,
    move_count,
    url,
    ingested_at,
    
    -- NEW: Game Type Classification
    CASE
      WHEN LOWER(event) LIKE '%rated%' THEN 'lichess_rated'
      WHEN LOWER(event) LIKE '%casual%' THEN 'lichess_casual'
      WHEN LOWER(event) LIKE '%arena%' OR LOWER(event) LIKE '%local%' OR LOWER(event) LIKE '%battle%' THEN 'tournament'
      ELSE 'unknown'
    END AS game_type,
    
    -- NEW: ELO Reliability Flags
    -- Lichess rated/casual games have reliable ELO in PGN headers
    -- Local/Arena engine tests do NOT have reliable ELO (user didn't set properly)
    CASE
      WHEN LOWER(event) LIKE '%rated%' OR LOWER(event) LIKE '%casual%' THEN TRUE
      WHEN LOWER(event) LIKE '%arena%' OR LOWER(event) LIKE '%local%' THEN FALSE
      WHEN LOWER(event) LIKE '%battle%' THEN TRUE  -- Lichess team battles have reliable ELO
      ELSE NULL
    END AS is_v7p3r_elo_reliable,
    
    CASE
      WHEN LOWER(event) LIKE '%rated%' OR LOWER(event) LIKE '%casual%' THEN TRUE
      WHEN LOWER(event) LIKE '%arena%' OR LOWER(event) LIKE '%local%' THEN FALSE
      WHEN LOWER(event) LIKE '%battle%' THEN TRUE  -- Lichess team battles have reliable ELO
      ELSE NULL
    END AS is_opponent_elo_reliable,
    
    -- NEW: Relative Opponent Strength (only meaningful if ELO reliable)
    CASE
      WHEN opponent_elo IS NULL OR v7p3r_elo IS NULL THEN 'unknown'
      WHEN opponent_elo > v7p3r_elo + 100 THEN 'stronger'
      WHEN opponent_elo < v7p3r_elo - 100 THEN 'weaker'
      ELSE 'equal'
    END AS relative_opponent_strength,
    
    -- NEW: Expected Score (ELO theory formula)
    -- Only valid when both ELOs are reliable
    CASE
      WHEN opponent_elo IS NOT NULL AND v7p3r_elo IS NOT NULL
        AND (LOWER(event) LIKE '%rated%' OR LOWER(event) LIKE '%casual%' OR LOWER(event) LIKE '%battle%')
      THEN 1 / (1 + POW(10, (opponent_elo - v7p3r_elo) / 400.0))
      ELSE NULL
    END AS expected_score,
    
    -- NEW: Actual Score (for performance comparison)
    CASE
      WHEN outcome = 'win' THEN 1.0
      WHEN outcome = 'draw' THEN 0.5
      WHEN outcome = 'loss' THEN 0.0
      ELSE NULL
    END AS actual_score
    
  FROM deduplicated
)
SELECT * FROM enhanced
"""

print("\n[1/3] Creating deduplicated + enhanced game_data table...")
print("-" * 80)
job = client.query(create_enhanced_query)
job.result()  # Wait for completion
print(f"✓ Created: game_data_enhanced")

# Step 2: Get summary statistics
stats_query = """
SELECT
  COUNT(*) as total_games,
  COUNT(DISTINCT game_id) as unique_game_ids,
  COUNT(DISTINCT engine_version) as versions,
  MIN(date) as first_game,
  MAX(date) as last_game,
  
  -- Game type breakdown
  COUNTIF(game_type = 'lichess_rated') as lichess_rated,
  COUNTIF(game_type = 'lichess_casual') as lichess_casual,
  COUNTIF(game_type = 'tournament') as tournament,
  COUNTIF(game_type = 'unknown') as unknown_type,
  
  -- ELO reliability
  COUNTIF(is_v7p3r_elo_reliable = TRUE) as reliable_elo_games,
  COUNTIF(is_v7p3r_elo_reliable = FALSE) as unreliable_elo_games,
  
  -- Opponent strength (where ELO reliable)
  COUNTIF(relative_opponent_strength = 'stronger' AND is_opponent_elo_reliable = TRUE) as vs_stronger,
  COUNTIF(relative_opponent_strength = 'equal' AND is_opponent_elo_reliable = TRUE) as vs_equal,
  COUNTIF(relative_opponent_strength = 'weaker' AND is_opponent_elo_reliable = TRUE) as vs_weaker
  
FROM `chess-engine-metrics-agent.conformed_layer.game_data_enhanced`
"""

print("\n[2/3] Gathering statistics...")
print("-" * 80)
stats = client.query(stats_query).to_dataframe()
print(stats.to_string(index=False))

# Step 3: Version breakdown
version_query = """
SELECT
  engine_version,
  COUNT(*) as games,
  COUNTIF(is_v7p3r_elo_reliable = TRUE) as reliable_elo_games,
  COUNTIF(outcome = 'win') as wins,
  COUNTIF(outcome = 'draw') as draws,
  COUNTIF(outcome = 'loss') as losses,
  ROUND(AVG(CASE WHEN is_v7p3r_elo_reliable = TRUE THEN v7p3r_elo END), 0) as avg_elo
FROM `chess-engine-metrics-agent.conformed_layer.game_data_enhanced`
WHERE engine_version IS NOT NULL
GROUP BY engine_version
ORDER BY MIN(date) DESC
LIMIT 15
"""

print("\n[3/3] Version breakdown (most recent 15):")
print("-" * 80)
versions = client.query(version_query).to_dataframe()
print(versions.to_string(index=False))

print("\n" + "=" * 80)
print("✓ PHASE 2 COMPLETE")
print("=" * 80)
print("\nNext steps:")
print("1. Review game_data_enhanced table")
print("2. Backup old game_data table")
print("3. Replace game_data with game_data_enhanced")
print("4. Rebuild reporting layer using only is_v7p3r_elo_reliable = TRUE games")
print("=" * 80)
