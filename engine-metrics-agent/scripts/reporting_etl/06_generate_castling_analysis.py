#!/usr/bin/env python3
"""
Generate castling_analysis reporting table

This ETL script aggregates game data by castling patterns to analyze
the impact of V7P3R and opponent castling choices on game outcomes.

Source: conformed_layer.game_data + game_summary
Target: reporting_layer.castling_analysis
Pattern: Manual ETL (run on-demand when new analysis needed)

Usage:
    python 06_generate_castling_analysis.py                    # Full refresh
    python 06_generate_castling_analysis.py --dry-run          # Preview SQL only
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
TARGET_TABLE = "castling_analysis"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('06_generate_castling_analysis.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def build_aggregation_query():
    """Build SQL query to aggregate performance by castling patterns"""
    
    query = f"""
    WITH castling_data AS (
        SELECT
            gd.outcome,
            gd.opponent_elo,
            gs.total_moves,
            gs.queen_traded,
            COALESCE(gs.v7p3r_castled, 'none') as v7p3r_castling,
            COALESCE(gs.opponent_castled, 'none') as opponent_castling,
            CONCAT(
                'v7p3r_', COALESCE(gs.v7p3r_castled, 'none'),
                '_opp_', COALESCE(gs.opponent_castled, 'none')
            ) as castling_pattern
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data` gd
        INNER JOIN `{PROJECT_ID}.{SOURCE_DATASET}.game_summary` gs
            ON gd.game_id = gs.game_id
    ),
    
    castling_stats AS (
        SELECT
            v7p3r_castling,
            opponent_castling,
            castling_pattern,
            COUNT(*) as total_games,
            COUNTIF(outcome = 'win') as wins,
            COUNTIF(outcome = 'loss') as losses,
            COUNTIF(outcome = 'draw') as draws,
            AVG(opponent_elo) as avg_opponent_elo,
            AVG(total_moves) as avg_game_length,
            COUNTIF(queen_traded = TRUE) as queen_trades
        FROM castling_data
        GROUP BY v7p3r_castling, opponent_castling, castling_pattern
    )
    
    SELECT
        v7p3r_castling,
        opponent_castling,
        castling_pattern,
        total_games,
        wins,
        losses,
        draws,
        
        -- Win rate
        SAFE_DIVIDE(wins, total_games) as win_rate,
        
        -- Opponent strength
        avg_opponent_elo,
        
        -- Game length
        avg_game_length,
        
        -- Castling timing (not available in source data)
        CAST(NULL AS INT64) as avg_v7p3r_castle_move,
        CAST(NULL AS INT64) as avg_opponent_castle_move,
        
        -- Tactical correlations
        SAFE_DIVIDE(queen_trades, total_games) as queen_trade_rate,
        
        -- Metadata
        CURRENT_TIMESTAMP() as last_updated
        
    FROM castling_stats
    WHERE total_games >= 10  -- Filter out rare patterns
    ORDER BY total_games DESC
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
            logger.info(f"\nPreview: {len(results)} castling patterns would be inserted:")
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
        logger.info(f"[OK] Inserted {rows_inserted} castling pattern records")
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
        COUNT(*) as castling_patterns,
        SUM(total_games) as total_games,
        ROUND(MIN(win_rate), 4) as min_win_rate,
        ROUND(MAX(win_rate), 4) as max_win_rate,
        ROUND(AVG(win_rate), 4) as avg_win_rate
    FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    """
    
    results = bq_client.query(validation_query).to_dataframe()
    
    logger.info("Validation Results:")
    logger.info(f"  - Total castling patterns: {results['castling_patterns'].iloc[0]}")
    logger.info(f"  - Total games aggregated: {results['total_games'].iloc[0]:,}")
    logger.info(f"  - Win rate range: {results['min_win_rate'].iloc[0]:.2%} - {results['max_win_rate'].iloc[0]:.2%}")
    logger.info(f"  - Average win rate: {results['avg_win_rate'].iloc[0]:.2%}")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Generate castling analysis reporting table")
    parser.add_argument('--dry-run', action='store_true', help="Preview SQL without executing")
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Castling Analysis ETL")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now()}")
    logger.info(f"Project: {PROJECT_ID}")
    logger.info(f"Source: {SOURCE_DATASET}.game_data + game_summary")
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
