#!/usr/bin/env python3
"""
Generate time_control_performance reporting table

This ETL script aggregates game data by time control format to analyze
V7P3R performance across different game speeds (bullet, blitz, rapid, classical).

Source: conformed_layer.game_data
Target: reporting_layer.time_control_performance
Pattern: Manual ETL (run on-demand when new analysis needed)

Usage:
    python 04_generate_time_control.py                    # Full refresh
    python 04_generate_time_control.py --dry-run          # Preview SQL only
"""

import argparse
import logging
import sys
from datetime import datetime
from google.cloud import bigquery

# Configuration
PROJECT_ID = "chess-engine-metrics-agent"
SOURCE_DATASET = "conformed_layer"
TARGET_DATASET = "reporting_layer"
TARGET_TABLE = "time_control_performance"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('04_generate_time_control.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def build_aggregation_query():
    """Build SQL query to aggregate performance by time control"""
    
    query = f"""
    WITH time_control_categorized AS (
        SELECT
            gd.*,
            -- Parse time control string (format: "180+2" = 180 seconds + 2 second increment)
            SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) as base_time_seconds,
            CASE
                WHEN SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) < 180 THEN 'bullet'
                WHEN SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) >= 180 
                     AND SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) < 480 THEN 'blitz'
                WHEN SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) >= 480 
                     AND SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) < 1500 THEN 'rapid'
                WHEN SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) >= 1500 THEN 'classical'
                ELSE 'unknown'
            END as time_category,
            CASE
                WHEN SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) < 180 THEN '<3min'
                WHEN SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) >= 180 
                     AND SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) < 480 THEN '3-8min'
                WHEN SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) >= 480 
                     AND SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) < 1500 THEN '8-25min'
                WHEN SAFE_CAST(SPLIT(gd.time_control, '+')[OFFSET(0)] AS INT64) >= 1500 THEN '25min+'
                ELSE 'unknown'
            END as time_range
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data` gd
        WHERE gd.time_control IS NOT NULL
    ),
    
    time_control_stats AS (
        SELECT
            time_category,
            time_range,
            COUNT(*) as total_games,
            COUNTIF(outcome = 'win') as wins,
            COUNTIF(outcome = 'loss') as losses,
            COUNTIF(outcome = 'draw') as draws,
            
            -- ELO metrics
            AVG(v7p3r_elo) as avg_v7p3r_elo,
            AVG(opponent_elo) as avg_opponent_elo,
            
            -- Color distribution
            COUNTIF(color = 'white') as games_as_white,
            COUNTIF(color = 'black') as games_as_black,
            
            -- ELO change
            AVG(CAST(rating_diff AS FLOAT64)) as avg_elo_change,
            
            -- Time forfeit rate
            COUNTIF(termination = 'Time forfeit') as time_forfeits,
            
            -- Game length
            AVG(move_count) as avg_game_length
            
        FROM time_control_categorized
        GROUP BY time_category, time_range
    )
    
    SELECT
        time_category as time_control_category,
        time_range as time_control_range,
        total_games,
        wins,
        losses,
        draws,
        
        -- Win rate
        SAFE_DIVIDE(wins, total_games) as win_rate,
        
        -- Game length
        avg_game_length,
        
        -- ELO metrics
        avg_v7p3r_elo,
        avg_opponent_elo,
        
        -- Color metrics
        games_as_white,
        games_as_black,
        SAFE_DIVIDE(games_as_white, total_games) - 0.5 as color_balance,
        
        -- ELO change
        avg_elo_change,
        
        -- Time pressure
        SAFE_DIVIDE(time_forfeits, total_games) as time_forfeit_rate,
        
        -- Metadata
        CURRENT_TIMESTAMP() as last_updated
        
    FROM time_control_stats
    ORDER BY
        CASE time_category
            WHEN 'bullet' THEN 1
            WHEN 'blitz' THEN 2
            WHEN 'rapid' THEN 3
            WHEN 'classical' THEN 4
            ELSE 5
        END
    """
    
    return query


def execute_full_refresh(bq_client, dry_run=False):
    """Delete existing data and rebuild from scratch"""
    logger.info("=" * 80)
    logger.info("FULL REFRESH MODE: Rebuilding entire table")
    logger.info("=" * 80)
    
    query = build_aggregation_query()
    
    if dry_run:
        logger.info("DRY RUN SQL QUERY:")
        logger.info("-" * 80)
        logger.info(query)
        logger.info("-" * 80)
        logger.info("\nExecuting query to preview results...")
        
        try:
            results = bq_client.query(query).to_dataframe()
            logger.info(f"\nPreview: {len(results)} time control categories would be inserted:")
            logger.info(f"\n{results.to_string()}")
            return
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"[FAIL] ETL FAILED: {e}")
            logger.error("=" * 80)
            raise
    
    # Delete existing data
    logger.info("Step 1: Deleting existing data from target table...")
    delete_query = f"DELETE FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}` WHERE TRUE"
    
    try:
        bq_client.query(delete_query).result()
        logger.info("[OK] Existing data deleted")
    except Exception as e:
        logger.error(f"Failed to delete existing data: {e}")
        raise
    
    # Insert aggregated data
    logger.info("Step 2: Inserting aggregated data...")
    insert_query = f"INSERT INTO `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}` {query}"
    
    try:
        job = bq_client.query(insert_query)
        result = job.result()
        
        rows_inserted = job.num_dml_affected_rows
        logger.info(f"[OK] Inserted {rows_inserted} time control records")
        logger.info(f"  - Bytes processed: {job.total_bytes_processed:,}")
        logger.info(f"  - Execution time: {job.ended - job.started}")
        
        return rows_inserted
    except Exception as e:
        logger.error(f"Failed to insert data: {e}")
        raise


def validate_results(bq_client):
    """Validate aggregated results"""
    logger.info("\nValidating results...")
    
    validation_query = f"""
    SELECT
        COUNT(*) as time_controls,
        SUM(total_games) as total_games,
        ROUND(MIN(win_rate), 4) as min_win_rate,
        ROUND(MAX(win_rate), 4) as max_win_rate,
        ROUND(AVG(win_rate), 4) as avg_win_rate
    FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    """
    
    results = bq_client.query(validation_query).to_dataframe()
    
    logger.info("Validation Results:")
    logger.info(f"  - Total time controls: {results['time_controls'].iloc[0]}")
    logger.info(f"  - Total games aggregated: {results['total_games'].iloc[0]:,}")
    logger.info(f"  - Win rate range: {results['min_win_rate'].iloc[0]:.2%} - {results['max_win_rate'].iloc[0]:.2%}")
    logger.info(f"  - Average win rate: {results['avg_win_rate'].iloc[0]:.2%}")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Generate time control performance reporting table")
    parser.add_argument('--dry-run', action='store_true', help="Preview SQL without executing")
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Time Control Performance ETL")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now()}")
    logger.info(f"Project: {PROJECT_ID}")
    logger.info(f"Source: {SOURCE_DATASET}.game_data")
    logger.info(f"Target: {TARGET_DATASET}.{TARGET_TABLE}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'FULL REFRESH'}")
    logger.info("=" * 80)
    
    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
        logger.info("[OK] BigQuery client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize BigQuery client: {e}")
        sys.exit(1)
    
    try:
        execute_full_refresh(bq_client, dry_run=args.dry_run)
        
        if not args.dry_run:
            validate_results(bq_client)
        
        logger.info("=" * 80)
        logger.info("[OK] ETL completed successfully")
        logger.info(f"Finished: {datetime.now()}")
        logger.info("=" * 80)
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"[FAIL] ETL FAILED: {e}")
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
