#!/usr/bin/env python3
"""
Ingest moves CSV to BigQuery conformed_layer.moves table

This script loads move-level granular data for deep positional and tactical analysis
from v7p3r_moves_latest.csv. This is a large dataset (~90MB, 1.35M rows) so it uses
batch processing to avoid memory issues.

Source: reporting_datasets/v7p3r_moves_latest.csv  
Target: conformed_layer.moves (14 columns with range partitioning)
Expected: 1,350,163 move records

Usage:
    python 08_ingest_moves.py                        # Full ingestion with batching
    python 08_ingest_moves.py --dry-run              # Preview without inserting
    python 08_ingest_moves.py --limit 1000           # Test with 1000 rows
    python 08_ingest_moves.py --batch-size 50000     # Custom batch size
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
TABLE_ID = "moves"
CSV_PATH = Path(__file__).parent.parent.parent.parent / "reporting_datasets" / "v7p3r_moves_latest.csv"
DEFAULT_BATCH_SIZE = 100000  # Process 100K rows at a time

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('08_ingest_moves.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def parse_clock_field(clock_str):
    """Parse clock field from HH:MM:SS format to total seconds (integer)
    
    Note: The CSV has clock as string "0:10:05" format. We convert to seconds.
    If we want to keep as TIME type, return the string as-is.
    For now, keeping as string to match BigQuery STRING type.
    """
    if pd.isna(clock_str):
        return None
    return str(clock_str).strip()


def validate_foreign_keys_sample(df, bq_client, sample_size=1000):
    """Validate sample of game_id values exist in game_data table"""
    logger.info(f"Validating foreign key: game_id -> game_data.game_id (sample of {sample_size})")
    
    # Sample unique game_ids
    unique_game_ids = df['game_id'].unique()
    sample_ids = unique_game_ids[:sample_size]
    
    # Query to check if game_ids exist
    game_ids_str = "', '".join(sample_ids)
    query = f"""
    SELECT game_id
    FROM `{PROJECT_ID}.{DATASET_ID}.game_data`
    WHERE game_id IN ('{game_ids_str}')
    """
    
    try:
        existing_ids = set(row.game_id for row in bq_client.query(query).result())
        checked_ids = set(sample_ids)
        missing_ids = checked_ids - existing_ids
        
        if missing_ids:
            logger.warning(f"WARNING: {len(missing_ids)}/{len(sample_ids)} game_ids not found in game_data table")
            logger.warning(f"Sample missing IDs: {list(missing_ids)[:5]}")
            logger.warning("These records will still be ingested, but may cause referential integrity issues")
        else:
            logger.info(f"✓ All sampled game_ids ({len(sample_ids)}) exist in game_data table")
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate foreign keys: {e}")
        logger.warning("Proceeding without validation - check data quality manually")
        return False


def load_csv_in_batches(csv_path, batch_size, limit=None):
    """Generator that yields batches of rows from CSV"""
    logger.info(f"Loading CSV from: {csv_path}")
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Get total row count first
    logger.info("Counting total rows...")
    total_rows = sum(1 for _ in open(csv_path, encoding='utf-8')) - 1  # Subtract header
    logger.info(f"CSV contains {total_rows:,} total rows")
    
    if limit:
        total_rows = min(total_rows, limit)
        logger.info(f"Limited to {total_rows:,} rows for testing")
    
    # Calculate number of batches
    num_batches = (total_rows + batch_size - 1) // batch_size
    logger.info(f"Processing in {num_batches} batches of {batch_size:,} rows")
    
    # Read CSV in chunks
    chunk_iterator = pd.read_csv(
        csv_path,
        chunksize=batch_size,
        nrows=limit
    )
    
    batch_num = 0
    for chunk in chunk_iterator:
        batch_num += 1
        
        # Transform data
        chunk['clock'] = chunk['clock'].apply(parse_clock_field)
        chunk['ingested_at'] = datetime.now()
        
        # Log batch info
        logger.info(f"Batch {batch_num}/{num_batches}: {len(chunk):,} rows")
        logger.info(f"  - Move range: {chunk['move_number'].min()}-{chunk['move_number'].max()}")
        logger.info(f"  - Game phases: {chunk['game_phase'].value_counts().to_dict()}")
        logger.info(f"  - Unique games: {chunk['game_id'].nunique()}")
        
        yield chunk, batch_num, num_batches


def ingest_batch_to_bigquery(df, batch_num, total_batches, client, table_ref, validate_fk=False):
    """Insert a single batch into BigQuery"""
    
    # Validate foreign keys on first batch only
    if validate_fk and batch_num == 1:
        validate_foreign_keys_sample(df, client, sample_size=1000)
    
    # Prepare job config
    job_config = bigquery.LoadJobConfig(
        write_disposition='WRITE_APPEND',
        create_disposition='CREATE_NEVER'  # Table must already exist
    )
    
    # Insert data
    logger.info(f"Inserting batch {batch_num}/{total_batches} ({len(df):,} rows)...")
    start_time = datetime.now()
    
    try:
        job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()  # Wait for completion
        
        duration = (datetime.now() - start_time).total_seconds()
        rows_per_sec = len(df) / duration if duration > 0 else 0
        logger.info(f"✓ Batch {batch_num} inserted in {duration:.1f}s ({rows_per_sec:.0f} rows/sec)")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to insert batch {batch_num}: {e}")
        import traceback
        traceback.print_exc()
        return False


def ingest_to_bigquery(csv_path, batch_size, limit=None, dry_run=False):
    """Insert data into BigQuery using batch processing"""
    logger.info(f"Target: {PROJECT_ID}.{DATASET_ID}.{TABLE_ID}")
    logger.info(f"Batch size: {batch_size:,} rows per batch")
    
    if dry_run:
        logger.info("DRY RUN: Previewing first batch only")
        for chunk, batch_num, total_batches in load_csv_in_batches(csv_path, batch_size, limit):
            logger.info(f"Would insert {len(chunk):,} rows in batch {batch_num}/{total_batches}")
            logger.info("Sample data (first 3 rows):")
            print(chunk.head(3).to_string())
            break  # Only show first batch in dry run
        return
    
    # Initialize BigQuery client
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    
    # Get initial row count
    try:
        query = f"SELECT COUNT(*) as count FROM `{table_ref}`"
        initial_count = list(client.query(query).result())[0].count
        logger.info(f"Table initially contains {initial_count:,} rows")
    except Exception as e:
        logger.warning(f"Could not get initial row count: {e}")
        initial_count = 0
    
    # Process batches
    total_ingested = 0
    failed_batches = 0
    overall_start = datetime.now()
    
    for chunk, batch_num, total_batches in load_csv_in_batches(csv_path, batch_size, limit):
        success = ingest_batch_to_bigquery(
            chunk, 
            batch_num, 
            total_batches, 
            client, 
            table_ref,
            validate_fk=(batch_num == 1)  # Validate FK on first batch only
        )
        
        if success:
            total_ingested += len(chunk)
        else:
            failed_batches += 1
            logger.error(f"Batch {batch_num} failed - continuing with next batch")
    
    # Summary
    overall_duration = (datetime.now() - overall_start).total_seconds()
    logger.info("=" * 70)
    logger.info("BATCH INGESTION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total rows ingested: {total_ingested:,}")
    logger.info(f"Failed batches: {failed_batches}")
    logger.info(f"Total time: {overall_duration:.1f} seconds ({overall_duration/60:.1f} minutes)")
    logger.info(f"Average throughput: {total_ingested/overall_duration:.0f} rows/second")
    
    # Verify final count
    try:
        query = f"SELECT COUNT(*) as count FROM `{table_ref}`"
        final_count = list(client.query(query).result())[0].count
        new_rows = final_count - initial_count
        logger.info(f"Table now contains {final_count:,} rows (+{new_rows:,} new)")
        
        # Sample recent data
        sample_query = f"""
        SELECT game_id, move_number, color, san, piece, is_capture, game_phase
        FROM `{table_ref}`
        ORDER BY ingested_at DESC
        LIMIT 5
        """
        logger.info("Recent ingested moves:")
        for row in client.query(sample_query).result():
            capture = " x" if row.is_capture else ""
            logger.info(f"  {row.game_id} move {row.move_number} ({row.game_phase}): {row.color} {row.piece}{capture} {row.san}")
            
    except Exception as e:
        logger.error(f"Failed to verify final count: {e}")


def main():
    """Main ingestion process"""
    parser = argparse.ArgumentParser(description='Ingest moves CSV to BigQuery with batching')
    parser.add_argument('--dry-run', action='store_true', help='Preview data without inserting')
    parser.add_argument('--limit', type=int, help='Limit number of rows for testing')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE, 
                       help=f'Rows per batch (default: {DEFAULT_BATCH_SIZE:,})')
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("V7P3R Moves Ingestion Starting")
    logger.info("=" * 70)
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Limit: {args.limit or 'None (full dataset)'}")
    logger.info(f"Batch size: {args.batch_size:,}")
    
    # Ingest to BigQuery with batching
    ingest_to_bigquery(CSV_PATH, args.batch_size, limit=args.limit, dry_run=args.dry_run)
    
    logger.info("=" * 70)
    logger.info("Ingestion Complete!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
