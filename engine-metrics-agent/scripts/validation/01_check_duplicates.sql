-- ============================================================================
-- DUPLICATE DETECTION VALIDATION
-- ============================================================================
-- Purpose: Identify duplicate game records across all source tables
-- Author: ETL Validation Framework
-- Date: 2026-05-03
--
-- This script checks for:
-- 1. Duplicate game_ids within each table
-- 2. Duplicate games across historical data dumps
-- 3. Impact on aggregated metrics
-- ============================================================================

-- Check 1: Duplicates in game_data (conformed layer)
-- ----------------------------------------------------------------------------
WITH game_data_duplicates AS (
  SELECT
    game_id,
    COUNT(*) as occurrences
  FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  GROUP BY game_id
  HAVING COUNT(*) > 1
)
SELECT
  'game_data' as table_name,
  COUNT(*) as duplicate_game_ids,
  SUM(occurrences) as total_duplicate_records,
  SUM(occurrences - 1) as inflated_count
FROM game_data_duplicates

UNION ALL

-- Check 2: Duplicates in game_summary (conformed layer)
-- ----------------------------------------------------------------------------
SELECT
  'game_summary' as table_name,
  COUNT(*) as duplicate_game_ids,
  SUM(occurrences) as total_duplicate_records,
  SUM(occurrences - 1) as inflated_count
FROM (
  SELECT
    game_id,
    COUNT(*) as occurrences
  FROM `chess-engine-metrics-agent.conformed_layer.game_summary`
  GROUP BY game_id
  HAVING COUNT(*) > 1
)

UNION ALL

-- Check 3: Duplicates in game_records (raw layer)
-- ----------------------------------------------------------------------------
SELECT
  'game_records' as table_name,
  COUNT(*) as duplicate_game_ids,
  SUM(occurrences) as total_duplicate_records,
  SUM(occurrences - 1) as inflated_count
FROM (
  SELECT
    game_id,
    COUNT(*) as occurrences
  FROM `chess-engine-metrics-agent.raw_layer.game_records`
  GROUP BY game_id
  HAVING COUNT(*) > 1
)

UNION ALL

-- Check 4: Cross-table duplicate analysis (game_data vs game_records)
-- ----------------------------------------------------------------------------
SELECT
  'cross_table_validation' as table_name,
  COUNT(DISTINCT gd.game_id) as games_in_conformed,
  COUNT(DISTINCT gr.game_id) as games_in_raw,
  COUNT(DISTINCT gd.game_id) - COUNT(DISTINCT gr.game_id) as difference
FROM `chess-engine-metrics-agent.conformed_layer.game_data` gd
FULL OUTER JOIN `chess-engine-metrics-agent.raw_layer.game_records` gr
  ON gd.game_id = gr.game_id

ORDER BY table_name;

-- ============================================================================
-- EXPECTED RESULTS:
-- If no duplicates exist:
--   - duplicate_game_ids should be 0 for all tables
--   - inflated_count should be 0
-- 
-- If duplicates exist:
--   - inflated_count shows how many extra records are skewing metrics
--   - These need to be deduplicated before final analysis
-- ============================================================================
