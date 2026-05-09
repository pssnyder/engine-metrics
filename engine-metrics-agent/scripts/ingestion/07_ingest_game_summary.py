#!/usr/bin/env python3
"""
Ingest game_summary CSV to BigQuery conformed_layer.game_summary table

This script loads game-level tactical/strategic summaries including castling patterns,
queen trades, and opening families from v7p3r_game_summary_enhanced_latest.csv.

Source: reporting_datasets/v7p3r_game_summary_enhanced_latest.csv
Target: conformed_layer.game_summary (8 columns)
Expected: 5,069 game summary records

Usage:
    python 07_ingest_game_summary.py                 # Full ingestion
    python 07_ingest_game_summary.py --dry-run       # Preview without inserting
    python 07_ingest_game_summary.py --limit 100     # Test with 100 rows
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from google.cloud import bigquery

# Configuration
PROJECT_ID = "chess-engine-metrics-agent"
DATASET_ID = "conformed_layer"
TABLE_ID = "game_summary"
CSV_PATH = Path(__file__).parent.parent.parent.parent / "reporting_datasets" / "v7p3r_game_summary_enhanced_latest.csv"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('07_ingest_game_summary.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def validate_foreign_keys(df, bq_client):
    """Validate that all game_id values exist in game_data table"""
    logger.info("Validating foreign key: game_id -> game_data.game_id")
    
    # Sample validation (check first 1000 game_ids for performance)
    sample_size = min(1000, len(df))
    sample_game_ids = df['game_id'].head(sample_size).tolist()
    
    # Query to check if game_ids exist
    game_ids_str = "', '".join(sample_game_ids)
    query = f"""
    SELECT game_id
    FROM `{PROJECT_ID}.{DATASET_ID}.game_data`
    WHERE game_id IN ('{game_ids_str}')
    """
    
    try:
        existing_ids = set(row.game_id for row in bq_client.query(query).result())
        checked_ids = set(sample_game_ids)
        missing_ids = checked_ids - existing_ids
        
        if missing_ids:
            logger.warning(f"WARNING: {len(missing_ids)} game_ids (in sample) not found in game_data table")
            logger.warning(f"Sample missing IDs: {list(missing_ids)[:5]}")
            logger.warning("These records will still be ingested, but may cause referential integrity issues")
        else:
            logger.info(f"✓ All sampled game_ids ({sample_size}) exist in game_data table")
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate foreign keys: {e}")
        logger.warning("Proceeding without validation - check data quality manually")
        return False


def load_and_transform_csv(csv_path, limit=None):
    """Load CSV and transform to match BigQuery schema"""
    logger.info(f"Loading CSV from: {csv_path}")
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Load CSV
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Apply limit if specified
    if limit:
        df = df.head(limit)
        logger.info(f"Limited to {len(df)} rows for testing")
    
    # Handle NULL values in castling columns (empty strings -> None)
    df['v7p3r_castled'] = df['v7p3r_castled'].replace('', None)
    df['opponent_castled'] = df['opponent_castled'].replace('', None)
    
    # Handle queen_traded NaN -> None for proper NULL handling
    df['queen_traded_move'] = df['queen_traded_move'].replace({pd.NA: None, float('nan'): None})
    
    # Add ingested_at timestamp
    df['ingested_at'] = datetime.now()
    
    # Log data quality metrics
    logger.info(f"Data quality:")
    logger.info(f"  - V7P3R castled: {df['v7p3r_castled'].value_counts().to_dict()}")
    logger.info(f"  - Opponent castled: {df['opponent_castled'].value_counts().to_dict()}")
    logger.info(f"  - Queen traded: {df['queen_traded'].sum()} games ({df['queen_traded'].sum()/len(df)*100:.1f}%)")
    logger.info(f"  - Opening families: {df['opening_family'].nunique()} unique")
    logger.info(f"  - Move count range: {df['total_moves'].min()}-{df['total_moves'].max()}")
    logger.info(f"  - Null values: {df.isnull().sum().sum()} total")
    
    return df


def ingest_to_bigquery(df, dry_run=False):
    """Insert data into BigQuery"""
    logger.info(f"Target: {PROJECT_ID}.{DATASET_ID}.{TABLE_ID}")
    
    if dry_run:
        logger.info("DRY RUN: Skipping BigQuery insertion")
        logger.info(f"Would insert {len(df)} rows")
        logger.info("Sample data (first 3 rows):")
        print(df.head(3).to_string())
        return
    
    # Initialize BigQuery client
    client = bigquery.Client(project=PROJECT_ID)
    
    # Validate foreign keys (note: game_data must be ingested first)
    validate_foreign_keys(df, client)
    
    # Prepare job config
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    job_config = bigquery.LoadJobConfig(
        write_disposition='WRITE_APPEND',
        create_disposition='CREATE_NEVER'  # Table must already exist
    )
    
    # Insert data
    logger.info(f"Inserting {len(df)} rows into BigQuery...")
    start_time = datetime.now()
    
    try:
        job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()  # Wait for completion
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✓ Successfully inserted {len(df)} rows in {duration:.1f} seconds")
        
        # Verify insertion
        query = f"SELECT COUNT(*) as count FROM `{table_ref}`"
        result = list(client.query(query).result())[0]
        logger.info(f"Table now contains {result.count} total rows")
        
        # Sample recent data
        sample_query = f"""
        SELECT game_id, v7p3r_castled, opponent_castled, queen_traded, opening_family
        FROM `{table_ref}`
        ORDER BY ingested_at DESC
        LIMIT 5
        """
        logger.info("Recent ingested records:")
        for row in client.query(sample_query).result():
            castling = f"V7P3R:{row.v7p3r_castled or 'none'} vs Opp:{row.opponent_castled or 'none'}"
            queen = "Q-traded" if row.queen_traded else "Queens on"
            logger.info(f"  {row.game_id}: {castling}, {queen}, {row.opening_family}")
            
    except Exception as e:
        logger.error(f"Failed to insert data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main ingestion process"""
    parser = argparse.ArgumentParser(description='Ingest game_summary CSV to BigQuery')
    parser.add_argument('--dry-run', action='store_true', help='Preview data without inserting')
    parser.add_argument('--limit', type=int, help='Limit number of rows for testing')
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("V7P3R Game Summary Ingestion Starting")
    logger.info("=" * 70)
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Limit: {args.limit or 'None (full dataset)'}")
    
    # Load and transform CSV
    df = load_and_transform_csv(CSV_PATH, limit=args.limit)
    
    # Ingest to BigQuery
    ingest_to_bigquery(df, dry_run=args.dry_run)
    
    logger.info("=" * 70)
    logger.info("Ingestion Complete!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
