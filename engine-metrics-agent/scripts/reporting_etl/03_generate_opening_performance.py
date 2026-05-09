#!/usr/bin/env python3
"""
Generate opening_performance reporting table

This ETL script aggregates game data by opening family to analyze
V7P3R performance across different opening repertoires.

Source: conformed_layer.game_data + game_summary
Target: reporting_layer.opening_performance
Pattern: Manual ETL (run on-demand when new analysis needed)

Usage:
    python 03_generate_opening_performance.py                    # Full refresh
    python 03_generate_opening_performance.py --dry-run          # Preview SQL only
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
TARGET_TABLE = "opening_performance"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('03_generate_opening_performance.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def build_aggregation_query():
    """Build SQL query to aggregate performance by opening family"""
    
    query = f"""
    WITH opening_stats AS (
        -- Join game_data with game_summary to get opening families and tactical data
        SELECT
            gs.opening_family,
            gd.eco,
            gd.outcome,
            gd.color,
            gd.opponent_elo,
            gs.total_moves,
            gs.v7p3r_castled,
            gs.opponent_castled,
            gs.queen_traded
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data` gd
        INNER JOIN `{PROJECT_ID}.{SOURCE_DATASET}.game_summary` gs
            ON gd.game_id = gs.game_id
        WHERE gs.opening_family IS NOT NULL
    ),
    
    opening_aggregates AS (
        -- Aggregate metrics by opening family
        SELECT
            opening_family,
            -- Use first ECO code as representative (openings may have multiple ECO codes)
            ANY_VALUE(eco) as eco_code,
            
            -- Game counts
            COUNT(*) as total_games,
            COUNTIF(outcome = 'win') as wins,
            COUNTIF(outcome = 'loss') as losses,
            COUNTIF(outcome = 'draw') as draws,
            
            -- Performance metrics
            AVG(opponent_elo) as avg_opponent_elo,
            
            -- Color distribution
            COUNTIF(color = 'white') as games_as_white,
            COUNTIF(color = 'black') as games_as_black,
            COUNTIF(color = 'white' AND outcome = 'win') as white_wins,
            COUNTIF(color = 'black' AND outcome = 'win') as black_wins,
            
            -- Game quality
            AVG(total_moves) as avg_game_length,
            
            -- Tactical patterns - V7P3R castling (most common)
            APPROX_TOP_COUNT(v7p3r_castled, 1)[OFFSET(0)].value as most_common_v7p3r_castle,
            
            -- Tactical patterns - Opponent castling (most common)
            APPROX_TOP_COUNT(opponent_castled, 1)[OFFSET(0)].value as most_common_opponent_castle,
            
            -- Queen trade rate
            COUNTIF(queen_traded = TRUE) as queen_trades
            
        FROM opening_stats
        GROUP BY opening_family
    )
    
    SELECT
        opening_family,
        eco_code,
        total_games,
        wins,
        losses,
        draws,
        
        -- Win rate
        SAFE_DIVIDE(wins, total_games) as win_rate,
        
        -- Averages
        avg_opponent_elo,
        
        -- Color preference
        games_as_white,
        games_as_black,
        CASE
            WHEN games_as_white > games_as_black * 1.5 THEN 'white'
            WHEN games_as_black > games_as_white * 1.5 THEN 'black'
            ELSE 'balanced'
        END as preferred_color,
        SAFE_DIVIDE(white_wins, games_as_white) as white_win_rate,
        SAFE_DIVIDE(black_wins, games_as_black) as black_win_rate,
        
        -- Game quality
        avg_game_length,
        
        -- Tactical patterns
        most_common_v7p3r_castle as avg_v7p3r_castled,
        most_common_opponent_castle as avg_opponent_castled,
        SAFE_DIVIDE(queen_trades, total_games) as queen_trade_rate,
        
        -- Metadata
        CURRENT_TIMESTAMP() as last_updated
        
    FROM opening_aggregates
    WHERE total_games >= 5  -- Filter out rare openings (less than 5 games)
    ORDER BY total_games DESC
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
        logger.info("DRY RUN SQL QUERY:")
        logger.info("-" * 80)
        logger.info(query)
        logger.info("-" * 80)
        logger.info("\nExecuting query to preview results (not writing to table)...")
        
        # Execute query to preview results
        try:
            results = bq_client.query(query).to_dataframe()
            logger.info(f"\nPreview: {len(results)} opening families would be inserted:")
            logger.info(f"\n{results.head(20).to_string()}")
            return
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"[FAIL] ETL FAILED: {e}")
            logger.error("=" * 80)
            raise
    
    # Step 1: Delete existing data
    logger.info("Step 1: Deleting existing data from target table...")
    delete_query = f"DELETE FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}` WHERE TRUE"
    
    try:
        bq_client.query(delete_query).result()
        logger.info("[OK] Existing data deleted")
    except Exception as e:
        logger.error(f"Failed to delete existing data: {e}")
        raise
    
    # Step 2: Insert aggregated data
    logger.info("Step 2: Inserting aggregated data...")
    insert_query = f"""
    INSERT INTO `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    {query}
    """
    
    try:
        job = bq_client.query(insert_query)
        result = job.result()
        
        rows_inserted = job.num_dml_affected_rows
        logger.info(f"[OK] Inserted {rows_inserted} opening family records")
        logger.info(f"  - Bytes processed: {job.total_bytes_processed:,}")
        logger.info(f"  - Execution time: {job.ended - job.started}")
        
        return rows_inserted
        
    except Exception as e:
        logger.error(f"Failed to insert data: {e}")
        raise


def validate_results(bq_client):
    """Validate aggregated results match expectations"""
    logger.info("\nValidating results...")
    
    validation_query = f"""
    SELECT
        COUNT(*) as opening_families,
        SUM(total_games) as total_games,
        ROUND(MIN(win_rate), 4) as min_win_rate,
        ROUND(MAX(win_rate), 4) as max_win_rate,
        ROUND(AVG(win_rate), 4) as avg_win_rate
    FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    """
    
    results = bq_client.query(validation_query).to_dataframe()
    
    logger.info("Validation Results:")
    logger.info(f"  - Total opening families: {results['opening_families'].iloc[0]}")
    logger.info(f"  - Total games aggregated: {results['total_games'].iloc[0]:,}")
    logger.info(f"  - Win rate range: {results['min_win_rate'].iloc[0]:.2%} - {results['max_win_rate'].iloc[0]:.2%}")
    logger.info(f"  - Average win rate: {results['avg_win_rate'].iloc[0]:.2%}")
    
    # Cross-check game count with source
    source_count_query = f"""
    SELECT COUNT(*) as total_games
    FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data` gd
    INNER JOIN `{PROJECT_ID}.{SOURCE_DATASET}.game_summary` gs
        ON gd.game_id = gs.game_id
    WHERE gs.opening_family IS NOT NULL
    """
    
    source_count = bq_client.query(source_count_query).to_dataframe()['total_games'].iloc[0]
    aggregated_count = results['total_games'].iloc[0]
    
    if source_count == aggregated_count:
        logger.info(f"[OK] Game count matches source: {source_count:,} games")
    else:
        logger.warning(f"[WARNING] Game count mismatch:")
        logger.warning(f"  - Source (game_data + game_summary): {source_count:,}")
        logger.warning(f"  - Aggregated: {aggregated_count:,}")
        logger.warning(f"  - Difference: {abs(source_count - aggregated_count):,}")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Generate opening performance reporting table")
    parser.add_argument('--dry-run', action='store_true', help="Preview SQL without executing")
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Opening Performance ETL")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now()}")
    logger.info(f"Project: {PROJECT_ID}")
    logger.info(f"Source: {SOURCE_DATASET}.game_data + game_summary")
    logger.info(f"Target: {TARGET_DATASET}.{TARGET_TABLE}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'FULL REFRESH'}")
    logger.info("=" * 80)
    
    # Initialize BigQuery client
    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
        logger.info("[OK] BigQuery client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize BigQuery client: {e}")
        sys.exit(1)
    
    try:
        # Execute ETL
        execute_full_refresh(bq_client, dry_run=args.dry_run)
        
        # Validate results (skip for dry run)
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
