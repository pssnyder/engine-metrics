#!/usr/bin/env python3
"""
Generate opponent_strength_performance reporting table

This ETL script aggregates game data by opponent ELO brackets to analyze
V7P3R performance against different strength opponents.

Source: conformed_layer.game_data
Target: reporting_layer.opponent_strength_performance
Pattern: Manual ETL (run on-demand when new analysis needed)

Usage:
    python 02_generate_opponent_strength.py                    # Full refresh
    python 02_generate_opponent_strength.py --dry-run          # Preview SQL only
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
TARGET_TABLE = "opponent_strength_performance"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('02_generate_opponent_strength.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def build_aggregation_query():
    """Build SQL query to aggregate performance by opponent ELO bracket"""
    
    query = f"""
    WITH elo_brackets AS (
        -- Categorize opponent ELO into brackets
        SELECT
            gd.*,
            CASE
                WHEN gd.opponent_elo < 1400 THEN '<1400'
                WHEN gd.opponent_elo >= 1400 AND gd.opponent_elo < 1600 THEN '1400-1600'
                WHEN gd.opponent_elo >= 1600 AND gd.opponent_elo < 1800 THEN '1600-1800'
                WHEN gd.opponent_elo >= 1800 AND gd.opponent_elo < 2000 THEN '1800-2000'
                WHEN gd.opponent_elo >= 2000 AND gd.opponent_elo < 2200 THEN '2000-2200'
                WHEN gd.opponent_elo >= 2200 THEN '2200+'
                ELSE 'Unknown'
            END as elo_bracket
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data` gd
        WHERE gd.opponent_elo IS NOT NULL
    ),
    
    bracket_stats AS (
        -- Aggregate metrics by ELO bracket
        SELECT
            elo_bracket,
            COUNT(*) as total_games,
            COUNTIF(outcome = 'win') as wins,
            COUNTIF(outcome = 'loss') as losses,
            COUNTIF(outcome = 'draw') as draws,
            
            -- Quality metrics (higher ELO opponents weight more)
            SUM(CASE WHEN outcome = 'win' THEN opponent_elo ELSE 0 END) / NULLIF(SUM(opponent_elo), 0) as quality_adjusted_win_rate,
            
            -- Game characteristics
            AVG(opponent_elo) as avg_opponent_elo,
            AVG(rating_diff) as avg_rating_diff,
            
            -- Color distribution
            COUNTIF(color = 'white') as games_as_white,
            COUNTIF(color = 'black') as games_as_black,
            COUNTIF(color = 'white' AND outcome = 'win') as white_wins,
            COUNTIF(color = 'black' AND outcome = 'win') as black_wins,
            
            -- ELO change metrics
            AVG(CAST(rating_diff AS FLOAT64)) as avg_elo_change
            
        FROM elo_brackets
        GROUP BY elo_bracket
    )
    
    SELECT
        elo_bracket,
        total_games,
        wins,
        losses,
        draws,
        
        -- Win rates
        SAFE_DIVIDE(wins, total_games) as win_rate,
        
        -- Game length (would need to join game_summary, skip for now)
        CAST(NULL AS FLOAT64) as avg_game_length,
        
        -- Averages
        avg_rating_diff,
        
        -- Color-specific metrics
        games_as_white,
        games_as_black,
        SAFE_DIVIDE(white_wins, games_as_white) as white_win_rate,
        SAFE_DIVIDE(black_wins, games_as_black) as black_win_rate,
        
        -- Color balance (0.5 = perfectly balanced, >0.5 favors white, <0.5 favors black)
        SAFE_DIVIDE(games_as_white, total_games) as color_balance,
        
        -- ELO progression
        avg_elo_change,
        
        -- Quality-adjusted win rate (performance weighted by opponent strength)
        quality_adjusted_win_rate,
        
        -- Metadata
        CURRENT_TIMESTAMP() as last_updated
        
    FROM bracket_stats
    ORDER BY
        CASE elo_bracket
            WHEN '<1400' THEN 1
            WHEN '1400-1600' THEN 2
            WHEN '1600-1800' THEN 3
            WHEN '1800-2000' THEN 4
            WHEN '2000-2200' THEN 5
            WHEN '2200+' THEN 6
            ELSE 7
        END
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
        logger.info(f"\nPreview: {len(df)} ELO brackets would be inserted:")
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
        logger.info(f"[OK] Inserted {row_count} ELO bracket records")
        
        # Log execution stats
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
        COUNT(*) as total_brackets,
        SUM(total_games) as total_games_aggregated,
        MIN(win_rate) as min_win_rate,
        MAX(win_rate) as max_win_rate,
        AVG(win_rate) as avg_win_rate
    FROM `{PROJECT_ID}.{TARGET_DATASET}.{TARGET_TABLE}`
    """
    
    try:
        results = bq_client.query(validation_query).to_dataframe()
        logger.info("Validation Results:")
        logger.info(f"  - Total ELO brackets: {results['total_brackets'].iloc[0]}")
        logger.info(f"  - Total games aggregated: {results['total_games_aggregated'].iloc[0]:,}")
        logger.info(f"  - Win rate range: {results['min_win_rate'].iloc[0]:.2%} - {results['max_win_rate'].iloc[0]:.2%}")
        logger.info(f"  - Average win rate: {results['avg_win_rate'].iloc[0]:.2%}")
        
        # Cross-check with source data
        source_query = f"""
        SELECT COUNT(*) as total_games
        FROM `{PROJECT_ID}.{SOURCE_DATASET}.game_data`
        WHERE opponent_elo IS NOT NULL
        """
        source_count = bq_client.query(source_query).to_dataframe()['total_games'].iloc[0]
        
        aggregated_count = results['total_games_aggregated'].iloc[0]
        if aggregated_count == source_count:
            logger.info(f"[OK] Game count matches source: {aggregated_count:,} games")
        else:
            logger.warning(f"[WARNING] Game count mismatch:")
            logger.warning(f"  - Source (game_data): {source_count:,}")
            logger.warning(f"  - Aggregated: {aggregated_count:,}")
            logger.warning(f"  - Difference: {abs(source_count - aggregated_count):,}")
        
        return True
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False


def main():
    """Main ETL execution"""
    parser = argparse.ArgumentParser(description="Generate opponent_strength_performance table")
    parser.add_argument('--dry-run', action='store_true', help="Preview SQL without executing")
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Opponent Strength Performance ETL")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now()}")
    logger.info(f"Project: {PROJECT_ID}")
    logger.info(f"Source: {SOURCE_DATASET}.game_data")
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
    
    # Execute ETL
    try:
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
        logger.error(f"[FAIL] ETL FAILED: {e}")
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
