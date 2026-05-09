#!/usr/bin/env python3
"""
Generate temporal_trends reporting table

This ETL script aggregates game data by date periods (daily, weekly, monthly)
to track V7P3R performance trends over time.

Source: conformed_layer.game_data
Target: reporting_layer.temporal_trends
Pattern: Manual ETL (run on-demand when new analysis needed)

Usage:
    python 05_generate_temporal_trends.py                    # Full refresh
    python 05_generate_temporal_trends.py --dry-run          # Preview SQL only
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
TARGET_TABLE = "temporal_trends"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('05_generate_temporal_trends.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def build_aggregation_query():
    """Build SQL query to aggregate performance by time periods"""
    
    query = f"""
    WITH daily_stats AS (
        SELECT
            date as date_period,
            'daily' as period_type,
            APPROX_TOP_COUNT(engine_version, 1)[OFFSET(0)].value as engine_version,
            COUNT(*) as total_games,
            COUNTIF(outcome = 'win') as wins,
            COUNTIF(outcome = 'loss') as losses,
            COUNTIF(outcome = 'draw') as draws,
            AVG(v7p3r_elo) as avg_v7p3r_elo,
            MIN(v7p3r_elo) as elo_start,
            MAX(v7p3r_elo) as elo_end,
            AVG(opponent_elo) as avg_opponent_elo,
            AVG(move_count) as avg_game_length
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data`
        WHERE date IS NOT NULL
        GROUP BY date
    ),
    
    weekly_stats AS (
        SELECT
            DATE_TRUNC(date, WEEK(MONDAY)) as date_period,
            'weekly' as period_type,
            APPROX_TOP_COUNT(engine_version, 1)[OFFSET(0)].value as engine_version,
            COUNT(*) as total_games,
            COUNTIF(outcome = 'win') as wins,
            COUNTIF(outcome = 'loss') as losses,
            COUNTIF(outcome = 'draw') as draws,
            AVG(v7p3r_elo) as avg_v7p3r_elo,
            MIN(v7p3r_elo) as elo_start,
            MAX(v7p3r_elo) as elo_end,
            AVG(opponent_elo) as avg_opponent_elo,
            AVG(move_count) as avg_game_length
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data`
        WHERE date IS NOT NULL
        GROUP BY DATE_TRUNC(date, WEEK(MONDAY))
    ),
    
    monthly_stats AS (
        SELECT
            DATE_TRUNC(date, MONTH) as date_period,
            'monthly' as period_type,
            APPROX_TOP_COUNT(engine_version, 1)[OFFSET(0)].value as engine_version,
            COUNT(*) as total_games,
            COUNTIF(outcome = 'win') as wins,
            COUNTIF(outcome = 'loss') as losses,
            COUNTIF(outcome = 'draw') as draws,
            AVG(v7p3r_elo) as avg_v7p3r_elo,
            MIN(v7p3r_elo) as elo_start,
            MAX(v7p3r_elo) as elo_end,
            AVG(opponent_elo) as avg_opponent_elo,
            AVG(move_count) as avg_game_length
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data`
        WHERE date IS NOT NULL
        GROUP BY DATE_TRUNC(date, MONTH)
    ),
    
    combined_periods AS (
        SELECT * FROM daily_stats
        UNION ALL
        SELECT * FROM weekly_stats
        UNION ALL
        SELECT * FROM monthly_stats
    )
    
    SELECT
        date_period,
        period_type,
        engine_version,
        total_games,
        wins,
        losses,
        draws,
        
        -- Win rate
        SAFE_DIVIDE(wins, total_games) as win_rate,
        
        -- ELO tracking
        avg_v7p3r_elo,
        elo_start,
        elo_end,
        elo_end - elo_start as elo_change,
        
        -- Opponent strength
        avg_opponent_elo,
        
        -- Game quality
        avg_game_length,
        
        -- Activity metrics
        CASE
            WHEN period_type = 'daily' THEN CAST(total_games AS FLOAT64)
            WHEN period_type = 'weekly' THEN SAFE_DIVIDE(total_games, 7.0)
            WHEN period_type = 'monthly' THEN SAFE_DIVIDE(total_games, 30.0)
        END as games_per_day,
        
        -- Metadata
        CURRENT_TIMESTAMP() as last_updated
        
    FROM combined_periods
    ORDER BY date_period DESC, 
        CASE period_type
            WHEN 'daily' THEN 1
            WHEN 'weekly' THEN 2
            WHEN 'monthly' THEN 3
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
            logger.info(f"\nPreview: {len(results)} time periods would be inserted:")
            logger.info(f"\n{results.head(30).to_string()}")
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
        logger.info(f"[OK] Inserted {rows_inserted} temporal period records")
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
        period_type,
        COUNT(*) as periods,
        SUM(total_games) as total_games,
        ROUND(AVG(win_rate), 4) as avg_win_rate
    FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    GROUP BY period_type
    ORDER BY period_type
    """
    
    results = bq_client.query(validation_query).to_dataframe()
    
    logger.info("Validation Results:")
    logger.info(f"\n{results.to_string(index=False)}")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Generate temporal trends reporting table")
    parser.add_argument('--dry-run', action='store_true', help="Preview SQL without executing")
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Temporal Trends ETL")
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
