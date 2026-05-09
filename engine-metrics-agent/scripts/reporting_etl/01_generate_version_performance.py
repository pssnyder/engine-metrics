#!/usr/bin/env python3
"""
Generate version_performance_summary reporting table

This ETL script aggregates game-level data from the conformed layer to create
a summary of V7P3R engine performance by version number.

Source: conformed_layer.game_data, conformed_layer.game_summary
Target: reporting_layer.version_performance_summary
Pattern: Manual ETL (run on-demand when new analysis needed)

Usage:
    python 01_generate_version_performance.py                    # Full refresh
    python 01_generate_version_performance.py --dry-run          # Preview SQL only
    python 01_generate_version_performance.py --incremental      # Append new versions only
"""

import argparse
import logging
import sys
from datetime import datetime
from google.cloud import bigquery

# Configuration
PROJECT_ID = "chess-engine-metrics-agent"
LOCATION = "us-central1"
SOURCE_DATASET = "conformed_layer"
TARGET_DATASET = "reporting_layer"
TARGET_TABLE = "version_performance_summary"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('01_generate_version_performance.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def build_aggregation_query():
    """Build SQL query to aggregate version performance metrics"""
    
    query = f"""
    WITH game_metrics AS (
        -- Aggregate game-level metrics by engine version
        SELECT
            gd.engine_version,
            COUNT(*) as total_games,
            
            -- Outcome counts
            COUNTIF(gd.outcome = 'win') as wins,
            COUNTIF(gd.outcome = 'loss') as losses,
            COUNTIF(gd.outcome = 'draw') as draws,
            
            -- ELO metrics
            AVG(gd.v7p3r_elo) as avg_v7p3r_elo,
            AVG(gd.opponent_elo) as avg_opponent_elo,
            AVG(gd.rating_diff) as avg_rating_diff,
            
            -- Game characteristics
            AVG(gs.total_moves) as avg_game_length,
            MIN(gd.date) as time_period_start,
            MAX(gd.date) as time_period_end,
            
            -- Color-specific metrics
            COUNTIF(gd.color = 'white') as games_as_white,
            COUNTIF(gd.color = 'black') as games_as_black,
            COUNTIF(gd.color = 'white' AND gd.outcome = 'win') as white_wins,
            COUNTIF(gd.color = 'black' AND gd.outcome = 'win') as black_wins
            
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data` gd
        LEFT JOIN `{PROJECT_ID}.{SOURCE_DATASET}.game_summary` gs
            ON gd.game_id = gs.game_id
        WHERE gd.engine_version IS NOT NULL
        GROUP BY gd.engine_version
    )
    
    SELECT
        engine_version,
        total_games,
        wins,
        losses,
        draws,
        
        -- Calculated rates
        SAFE_DIVIDE(wins, total_games) as win_rate,
        SAFE_DIVIDE(losses, total_games) as loss_rate,
        SAFE_DIVIDE(draws, total_games) as draw_rate,
        
        -- ELO metrics
        avg_v7p3r_elo,
        avg_opponent_elo,
        avg_rating_diff,
        avg_game_length,
        
        -- Time period
        time_period_start,
        time_period_end,
        
        -- Color distribution
        games_as_white,
        games_as_black,
        
        -- Color-specific win rates
        SAFE_DIVIDE(white_wins, games_as_white) as white_win_rate,
        SAFE_DIVIDE(black_wins, games_as_black) as black_win_rate,
        
        -- Metadata
        CURRENT_TIMESTAMP() as last_updated
        
    FROM game_metrics
    ORDER BY engine_version
    """
    
    return query


def build_incremental_query():
    """Build SQL query for incremental updates (new versions only)"""
    
    query = f"""
    WITH existing_versions AS (
        SELECT DISTINCT engine_version
        FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    ),
    
    game_metrics AS (
        -- Only aggregate versions not in target table
        SELECT
            gd.engine_version,
            COUNT(*) as total_games,
            COUNTIF(gd.outcome = 'win') as wins,
            COUNTIF(gd.outcome = 'loss') as losses,
            COUNTIF(gd.outcome = 'draw') as draws,
            AVG(gd.v7p3r_elo) as avg_v7p3r_elo,
            AVG(gd.opponent_elo) as avg_opponent_elo,
            AVG(gd.rating_diff) as avg_rating_diff,
            AVG(gs.total_moves) as avg_game_length,
            MIN(gd.date) as time_period_start,
            MAX(gd.date) as time_period_end,
            COUNTIF(gd.color = 'white') as games_as_white,
            COUNTIF(gd.color = 'black') as games_as_black,
            COUNTIF(gd.color = 'white' AND gd.outcome = 'win') as white_wins,
            COUNTIF(gd.color = 'black' AND gd.outcome = 'win') as black_wins
            
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data` gd
        LEFT JOIN `{PROJECT_ID}.{SOURCE_DATASET}.game_summary` gs
            ON gd.game_id = gs.game_id
        WHERE gd.engine_version IS NOT NULL
            AND gd.engine_version NOT IN (SELECT engine_version FROM existing_versions)
        GROUP BY gd.engine_version
    )
    
    SELECT
        engine_version,
        total_games,
        wins,
        losses,
        draws,
        SAFE_DIVIDE(wins, total_games) as win_rate,
        SAFE_DIVIDE(losses, total_games) as loss_rate,
        SAFE_DIVIDE(draws, total_games) as draw_rate,
        avg_v7p3r_elo,
        avg_opponent_elo,
        avg_rating_diff,
        avg_game_length,
        time_period_start,
        time_period_end,
        games_as_white,
        games_as_black,
        SAFE_DIVIDE(white_wins, games_as_white) as white_win_rate,
        SAFE_DIVIDE(black_wins, games_as_black) as black_win_rate,
        CURRENT_TIMESTAMP() as last_updated
        
    FROM game_metrics
    ORDER BY engine_version
    """
    
    return query


def execute_full_refresh(bq_client, dry_run=False):
    """Delete existing data and rebuild from scratch"""
    logger.info("=" * 80)
    logger.info("FULL REFRESH MODE: Rebuilding entire table")
    logger.info("=" * 80)
    
    # Build aggregation query
    query = build_aggregation_query()
    
    if dry_run:
        logger.info("DRY RUN - SQL Preview:")
        logger.info("-" * 80)
        logger.info(query)
        logger.info("-" * 80)
        
        # Execute query to preview results
        logger.info("\nExecuting query to preview results (not writing to table)...")
        df = bq_client.query(query).to_dataframe()
        logger.info(f"\nPreview: {len(df)} versions would be inserted:")
        logger.info("\n" + df.to_string())
        return df
    
    # Execute full refresh
    logger.info("Step 1: Deleting existing data from target table...")
    delete_query = f"DELETE FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}` WHERE TRUE"
    
    try:
        bq_client.query(delete_query).result()
        logger.info("[OK] Existing data deleted")
    except Exception as e:
        logger.error(f"Failed to delete existing data: {e}")
        raise
    
    logger.info("Step 2: Inserting aggregated data...")
    insert_query = f"""
    INSERT INTO `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    {query}
    """
    
    try:
        job = bq_client.query(insert_query)
        result = job.result()
        
        # Get row count
        row_count = job.num_dml_affected_rows
        logger.info(f"[OK] Inserted {row_count} version records")
        
        # Log execution stats
        logger.info(f"  - Bytes processed: {job.total_bytes_processed:,}")
        logger.info(f"  - Execution time: {job.ended - job.started}")
        
        return row_count
        
    except Exception as e:
        logger.error(f"Failed to insert data: {e}")
        raise


def execute_incremental(bq_client, dry_run=False):
    """Append only new versions not in target table"""
    logger.info("=" * 80)
    logger.info("INCREMENTAL MODE: Appending new versions only")
    logger.info("=" * 80)
    
    # Build incremental query
    query = build_incremental_query()
    
    if dry_run:
        logger.info("DRY RUN - SQL Preview:")
        logger.info("-" * 80)
        logger.info(query)
        logger.info("-" * 80)
        
        logger.info("\nExecuting query to preview results...")
        df = bq_client.query(query).to_dataframe()
        
        if len(df) == 0:
            logger.info("\n[OK] No new versions to add (all versions already in table)")
        else:
            logger.info(f"\nPreview: {len(df)} new versions would be added:")
            logger.info("\n" + df.to_string())
        return df
    
    # Execute incremental insert
    logger.info("Inserting new versions...")
    insert_query = f"""
    INSERT INTO `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    {query}
    """
    
    try:
        job = bq_client.query(insert_query)
        result = job.result()
        row_count = job.num_dml_affected_rows
        
        if row_count == 0:
            logger.info("[OK] No new versions to add (all versions already in table)")
        else:
            logger.info(f"[OK] Inserted {row_count} new version records")
            logger.info(f"  - Bytes processed: {job.total_bytes_processed:,}")
            logger.info(f"  - Execution time: {job.ended - job.started}")
        
        return row_count
        
    except Exception as e:
        logger.error(f"Failed to insert data: {e}")
        raise


def validate_results(bq_client):
    """Validate inserted data quality"""
    logger.info("\nValidating results...")
    
    validation_query = f"""
    SELECT
        COUNT(*) as total_versions,
        SUM(total_games) as total_games_aggregated,
        MIN(time_period_start) as earliest_game,
        MAX(time_period_end) as latest_game,
        AVG(win_rate) as avg_win_rate,
        MIN(win_rate) as min_win_rate,
        MAX(win_rate) as max_win_rate
    FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    """
    
    try:
        results = bq_client.query(validation_query).to_dataframe()
        logger.info("Validation Results:")
        logger.info(f"  - Total versions: {results['total_versions'].iloc[0]}")
        logger.info(f"  - Total games aggregated: {results['total_games_aggregated'].iloc[0]:,}")
        logger.info(f"  - Date range: {results['earliest_game'].iloc[0]} to {results['latest_game'].iloc[0]}")
        logger.info(f"  - Win rate range: {results['min_win_rate'].iloc[0]:.2%} - {results['max_win_rate'].iloc[0]:.2%}")
        logger.info(f"  - Average win rate: {results['avg_win_rate'].iloc[0]:.2%}")
        
        # Cross-check with source data
        source_query = f"""
        SELECT COUNT(*) as total_games
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data`
        WHERE engine_version IS NOT NULL
        """
        source_count = bq_client.query(source_query).to_dataframe()['total_games'].iloc[0]
        
        aggregated_count = results['total_games_aggregated'].iloc[0]
        if aggregated_count == source_count:
            logger.info(f"[OK] Game count matches source: {aggregated_count:,} games")
        else:
            logger.warning(f"⚠ Game count mismatch:")
            logger.warning(f"  - Source (game_data): {source_count:,}")
            logger.warning(f"  - Aggregated: {aggregated_count:,}")
            logger.warning(f"  - Difference: {abs(source_count - aggregated_count):,}")
        
        return True
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False


def main():
    """Main ETL execution"""
    parser = argparse.ArgumentParser(description="Generate version_performance_summary table")
    parser.add_argument('--dry-run', action='store_true', help="Preview SQL without executing")
    parser.add_argument('--incremental', action='store_true', help="Append new versions only")
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Version Performance Summary ETL")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now()}")
    logger.info(f"Project: {PROJECT_ID}")
    logger.info(f"Source: {SOURCE_DATASET}.game_data + game_summary")
    logger.info(f"Target: {TARGET_DATASET}.{TARGET_TABLE}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'INCREMENTAL' if args.incremental else 'FULL REFRESH'}")
    logger.info("=" * 80)
    
    # Initialize BigQuery client
    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
        logger.info("[OK] BigQuery client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize BigQuery client: {e}")
        sys.exit(1)
    
    # Execute ETL
    try:
        if args.incremental:
            row_count = execute_incremental(bq_client, dry_run=args.dry_run)
        else:
            row_count = execute_full_refresh(bq_client, dry_run=args.dry_run)
        
        # Validate results (skip for dry run)
        if not args.dry_run:
            validate_results(bq_client)
        
        logger.info("=" * 80)
        logger.info(f"[OK] ETL completed successfully")
        logger.info(f"Finished: {datetime.now()}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"✗ ETL FAILED: {e}")
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
