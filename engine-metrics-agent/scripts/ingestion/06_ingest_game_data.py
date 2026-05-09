#!/usr/bin/env python3
"""
Ingest game_data CSV to BigQuery conformed_layer.game_data table

This script loads historical game-level metadata from v7p3r_game_data_latest.csv
into the conformed layer. This CSV represents the baseline analytics dataset
that can be validated against fresh PGN data in the game_records table.

Source: reporting_datasets/v7p3r_game_data_latest.csv
Target: conformed_layer.game_data (18 columns)
Expected: 18,336 game records

Usage:
    python 06_ingest_game_data.py                    # Full ingestion
    python 06_ingest_game_data.py --dry-run          # Preview without inserting
    python 06_ingest_game_data.py --limit 100        # Test with 100 rows
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
TABLE_ID = "game_data"
CSV_PATH = Path(__file__).parent.parent.parent.parent / "reporting_datasets" / "v7p3r_game_data_latest.csv"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('06_ingest_game_data.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def parse_date_field(date_str):
    """Parse date field from YYYY.MM.DD format to proper date object"""
    if pd.isna(date_str):
        return None
    try:
        # Format: 2025.09.26 -> datetime.date(2025, 9, 26)
        date_str = str(date_str).strip()
        if '.' in date_str:
            parts = date_str.split('.')
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            from datetime import date
            return date(year, month, day)
        else:
            # Try ISO format
            return pd.to_datetime(date_str).date()
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return None


def parse_time_field(time_str):
    """Parse time field from HH:MM:SS format to proper time object"""
    if pd.isna(time_str):
        return None
    try:
        from datetime import time
        time_str = str(time_str).strip()
        parts = time_str.split(':')
        hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
        return time(hour, minute, second)
    except Exception as e:
        logger.warning(f"Failed to parse time '{time_str}': {e}")
        return None


def validate_foreign_keys(df, bq_client):
    """Validate that all engine_version values exist in engine_versions table"""
    logger.info("Validating foreign key: engine_version -> engine_versions.engine_version")
    
    # Get unique engine versions from CSV
    unique_versions = df['engine_version'].dropna().unique()
    logger.info(f"Found {len(unique_versions)} unique engine versions in CSV")
    
    # Query existing versions in engine_versions table
    query = f"""
    SELECT DISTINCT engine_version 
    FROM `{PROJECT_ID}.{DATASET_ID}.engine_versions`
    """
    
    try:
        existing_versions = set(row.engine_version for row in bq_client.query(query).result())
        logger.info(f"Found {len(existing_versions)} versions in engine_versions table")
        
        # Check for missing versions
        missing_versions = set(unique_versions) - existing_versions
        
        if missing_versions:
            logger.warning(f"WARNING: {len(missing_versions)} engine versions not in engine_versions table:")
            for version in sorted(missing_versions):
                logger.warning(f"  - {version}")
            logger.warning("These games will still be ingested, but may cause referential integrity issues")
        else:
            logger.info("✓ All engine versions exist in engine_versions table")
            
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
    
    # Transform date field from YYYY.MM.DD to date object
    logger.info("Transforming date field from YYYY.MM.DD to date objects")
    df['date'] = df['date'].apply(parse_date_field)
    
    # Transform time field from HH:MM:SS to time object
    logger.info("Transforming time field from HH:MM:SS to time objects")
    df['time'] = df['time'].apply(parse_time_field)
    
    # Add ingested_at timestamp
    df['ingested_at'] = datetime.now()
    
    # Log data quality metrics
    logger.info(f"Data quality:")
    logger.info(f"  - Date range: {df['date'].min()} to {df['date'].max()}")
    logger.info(f"  - Engine versions: {df['engine_version'].nunique()} unique")
    logger.info(f"  - ELO range: {df['v7p3r_elo'].min()}-{df['v7p3r_elo'].max()}")
    logger.info(f"  - Opponent ELO range: {df['opponent_elo'].min()}-{df['opponent_elo'].max()}")
    logger.info(f"  - Time controls: {df['time_control'].nunique()} unique")
    logger.info(f"  - Outcomes: {df['outcome'].value_counts().to_dict()}")
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
    
    # Validate foreign keys
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
        SELECT game_id, date, engine_version, color, outcome, v7p3r_elo, opponent_elo
        FROM `{table_ref}`
        ORDER BY ingested_at DESC
        LIMIT 5
        """
        logger.info("Recent ingested records:")
        for row in client.query(sample_query).result():
            logger.info(f"  {row.game_id}: v{row.engine_version} as {row.color} -> {row.outcome} ({row.v7p3r_elo} vs {row.opponent_elo})")
            
    except Exception as e:
        logger.error(f"Failed to insert data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main ingestion process"""
    parser = argparse.ArgumentParser(description='Ingest game_data CSV to BigQuery')
    parser.add_argument('--dry-run', action='store_true', help='Preview data without inserting')
    parser.add_argument('--limit', type=int, help='Limit number of rows for testing')
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("V7P3R Game Data Ingestion Starting")
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
