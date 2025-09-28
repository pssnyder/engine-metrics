#!/usr/bin/env python3
"""
Full batch ingestion script to process ALL files in the bucket
and understand the complete data landscape
"""

import json
import logging
import time
from datetime import datetime
from ingest_layer import IngestLayer
from google.cloud import bigquery

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_ingestion.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_full_ingestion():
    """Run complete batch ingestion of all files in the bucket"""
    logger.info("=" * 60)
    logger.info("STARTING FULL BATCH INGESTION")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        # Clear processed files to start fresh
        with open('processed_files.json', 'w') as f:
            json.dump([], f)
        logger.info("Cleared processed files - starting fresh")
        
        # Initialize ingest layer
        logger.info("Initializing Ingest Layer...")
        ingest = IngestLayer()
        
        # Get all files to process
        logger.info("Scanning bucket for all files...")
        all_files = ingest.storage_monitor.scan_for_new_files()
        
        # Categorize files by type and size
        file_categories = {
            'pgn': {'small': [], 'large': []},
            'json': {'small': [], 'large': []},
            'md': {'small': [], 'large': []},
            'other': {'small': [], 'large': []}
        }
        
        size_threshold = 1024  # 1KB threshold
        
        for blob in all_files:
            if blob.name.endswith('/'):  # Skip directories
                continue
                
            # Categorize by extension
            if blob.name.endswith('.pgn'):
                category = 'pgn'
            elif blob.name.endswith('.json'):
                category = 'json'
            elif blob.name.endswith('.md'):
                category = 'md'
            else:
                category = 'other'
            
            # Categorize by size
            size_category = 'large' if (blob.size and blob.size > size_threshold) else 'small'
            file_categories[category][size_category].append(blob)
        
        # Print categorization summary
        logger.info("FILE CATEGORIZATION SUMMARY:")
        logger.info("-" * 40)
        total_files = 0
        for category, sizes in file_categories.items():
            small_count = len(sizes['small'])
            large_count = len(sizes['large'])
            category_total = small_count + large_count
            total_files += category_total
            
            if category_total > 0:
                logger.info(f"{category.upper():>6}: {category_total:3} files ({small_count:3} small, {large_count:3} large)")
                
                # Show sample large files
                if large_count > 0:
                    logger.info(f"       Sample large {category} files:")
                    for blob in sizes['large'][:3]:
                        size_kb = (blob.size or 0) / 1024
                        logger.info(f"         - {blob.name} ({size_kb:.1f} KB)")
        
        logger.info(f"TOTAL:  {total_files:3} files to process")
        logger.info("-" * 40)
        
        # Get BigQuery client for monitoring
        bq_client = bigquery.Client(project='chess-engine-metrics-agent')
        
        # Get initial row counts
        initial_counts = {}
        tables = ['pgn_games', 'analysis_results', 'documentation']
        for table in tables:
            query = f"SELECT COUNT(*) as count FROM chess_engine_data_lake.{table}"
            result = list(bq_client.query(query).result())[0]
            initial_counts[table] = result.count
            logger.info(f"Initial {table}: {result.count} rows")
        
        # Process all files using the batch ingestion method
        logger.info("\nStarting batch processing...")
        logger.info("=" * 60)
        
        results = ingest.storage_monitor.run_batch_ingestion()
        
        processing_time = time.time() - start_time
        
        # Get final row counts
        logger.info("\nBATCH PROCESSING COMPLETED!")
        logger.info("=" * 60)
        logger.info(f"Processing time: {processing_time:.1f} seconds ({processing_time/60:.1f} minutes)")
        logger.info(f"Files processed: {results['processed']}")
        logger.info(f"Files failed: {results['failed']}")
        logger.info(f"Files skipped: {results['skipped']}")
        
        # Show data growth
        logger.info("\nDATA INGESTION RESULTS:")
        logger.info("-" * 40)
        total_new_records = 0
        for table in tables:
            query = f"SELECT COUNT(*) as count FROM chess_engine_data_lake.{table}"
            result = list(bq_client.query(query).result())[0]
            final_count = result.count
            new_records = final_count - initial_counts[table]
            total_new_records += new_records
            
            logger.info(f"{table:>18}: {initial_counts[table]:4} -> {final_count:4} ({new_records:+4} new)")
        
        logger.info(f"{'TOTAL NEW RECORDS':>18}: {total_new_records:4}")
        logger.info("-" * 40)
        
        # Sample recent data from each table
        if total_new_records > 0:
            logger.info("\nSAMPLE INGESTED DATA:")
            logger.info("-" * 40)
            
            # Sample PGN games
            pgn_query = """
            SELECT game_id, white, black, result, move_count, white_elo, black_elo 
            FROM chess_engine_data_lake.pgn_games 
            ORDER BY ingested_at DESC 
            LIMIT 5
            """
            logger.info("Recent PGN Games:")
            for row in bq_client.query(pgn_query).result():
                elo_info = f"({row.white_elo or '?'} vs {row.black_elo or '?'})"
                logger.info(f"  {row.white} vs {row.black} = {row.result} - {row.move_count} moves {elo_info}")
            
            # Sample analysis results
            analysis_query = """
            SELECT analysis_id, engine_version, analysis_type 
            FROM chess_engine_data_lake.analysis_results 
            ORDER BY ingested_at DESC 
            LIMIT 5
            """
            logger.info("\nRecent Analysis Results:")
            for row in bq_client.query(analysis_query).result():
                logger.info(f"  {row.analysis_id}: {row.engine_version} - {row.analysis_type}")
            
            # Sample documentation
            doc_query = """
            SELECT doc_id, title, doc_type 
            FROM chess_engine_data_lake.documentation 
            ORDER BY ingested_at DESC 
            LIMIT 5
            """
            logger.info("\nRecent Documentation:")
            for row in bq_client.query(doc_query).result():
                logger.info(f"  {row.title} ({row.doc_type})")
        
        # Data landscape summary for Transform Layer planning
        logger.info("\nDATA LANDSCAPE FOR TRANSFORM LAYER:")
        logger.info("=" * 60)
        
        # Engine versions found
        engine_query = """
        SELECT 
            REGEXP_EXTRACT(white, r'(V7P3R|SlowMate|C0BR4|Cece)_?v?([0-9.]+)?') as engine,
            COUNT(*) as games
        FROM chess_engine_data_lake.pgn_games 
        WHERE REGEXP_EXTRACT(white, r'(V7P3R|SlowMate|C0BR4|Cece)_?v?([0-9.]+)?') IS NOT NULL
        GROUP BY engine
        ORDER BY games DESC
        LIMIT 10
        """
        logger.info("Chess Engines Found:")
        for row in bq_client.query(engine_query).result():
            if row.engine:
                logger.info(f"  {row.engine}: {row.games} games as white")
        
        # Date range of games
        date_query = """
        SELECT 
            MIN(date) as earliest_game,
            MAX(date) as latest_game,
            COUNT(DISTINCT date) as unique_dates
        FROM chess_engine_data_lake.pgn_games 
        WHERE date IS NOT NULL
        """
        result = list(bq_client.query(date_query).result())[0]
        logger.info(f"\nGame Date Range:")
        logger.info(f"  Earliest: {result.earliest_game}")
        logger.info(f"  Latest: {result.latest_game}")
        logger.info(f"  Unique dates: {result.unique_dates}")
        
        # Success/failure rates
        success_rate = (results['processed'] / (results['processed'] + results['failed']) * 100) if (results['processed'] + results['failed']) > 0 else 0
        logger.info(f"\nOVERALL SUCCESS RATE: {success_rate:.1f}%")
        
        logger.info("\nFULL INGESTION COMPLETED SUCCESSFULLY!")
        logger.info("Ready for Transform Layer implementation.")
        
    except Exception as e:
        logger.error(f"Full ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        total_time = time.time() - start_time
        logger.info(f"\nTotal execution time: {total_time:.1f} seconds")

if __name__ == "__main__":
    run_full_ingestion()