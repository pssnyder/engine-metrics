#!/usr/bin/env python3
"""
Test BigQuery insertion with parsed data to identify insertion issues
"""

import json
import logging
import sys
from datetime import datetime, date
import pandas as pd
from google.cloud import bigquery, storage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_insertion.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_bigquery_insertion():
    """Test actual BigQuery insertion with sample data"""
    logger.info("=== Testing BigQuery Insertion ===")
    
    try:
        client = bigquery.Client(project='chess-engine-metrics-agent')
        
        # Test data that matches our parsed structure
        test_records = [
            {
                'game_id': 'debug_test_001',
                'event': 'Debug Test Event',
                'site': 'Debug Site',
                'date': date(2025, 9, 26),  # Proper date object
                'round': '1',
                'white': 'Debug White',
                'black': 'Debug Black',
                'result': '1-0',
                'white_elo': None,
                'black_elo': None,
                'time_control': '10+5',
                'opening': 'Debug Opening',
                'moves': 'e4 e5 Nf3 Nc6 Bb5',
                'move_count': 5,
                'game_duration': 600,
                'termination': 'Normal',
                'source_file': 'debug_test.pgn',
                'ingested_at': datetime.now(),
                'file_modified_at': datetime.now()
            },
            {
                'game_id': 'debug_test_002',
                'event': 'Debug Test Event',
                'site': 'Debug Site',
                'date': None,  # Test with None date
                'round': '2',
                'white': 'Debug White 2',
                'black': 'Debug Black 2',
                'result': '0-1',
                'white_elo': None,
                'black_elo': None,
                'time_control': None,
                'opening': None,
                'moves': '',  # Empty moves (like the real PGN)
                'move_count': 0,
                'game_duration': None,
                'termination': None,
                'source_file': 'debug_test_2.pgn',
                'ingested_at': datetime.now(),
                'file_modified_at': datetime.now()
            }
        ]
        
        # Test insertion
        df = pd.DataFrame(test_records)
        table_id = 'chess-engine-metrics-agent.chess_engine_data_lake.pgn_games'
        
        logger.info(f"Attempting to insert {len(test_records)} test records")
        logger.info(f"DataFrame shape: {df.shape}")
        logger.info(f"DataFrame columns: {list(df.columns)}")
        
        # Check data types
        logger.info("DataFrame dtypes:")
        for col, dtype in df.dtypes.items():
            logger.info(f"  {col}: {dtype}")
            
        # Test insertion
        job_config = bigquery.LoadJobConfig(write_disposition='WRITE_APPEND')
        
        try:
            job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
            job.result()  # Wait for completion
            
            logger.info("SUCCESS: Test records inserted!")
            
            # Check table count
            query = f"SELECT COUNT(*) as count FROM `{table_id}`"
            query_job = client.query(query)
            result = list(query_job.result())[0]
            logger.info(f"Table now has {result.count} total rows")
            
            # Show recent records
            query = f"SELECT game_id, white, black, moves, move_count FROM `{table_id}` WHERE source_file LIKE 'debug_%' ORDER BY ingested_at DESC LIMIT 5"
            query_job = client.query(query)
            
            logger.info("Recent test records:")
            for row in query_job.result():
                logger.info(f"  {row.game_id}: {row.white} vs {row.black} ({row.move_count} moves)")
                
        except Exception as e:
            logger.error(f"BigQuery insertion failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        logger.error(f"BigQuery setup failed: {e}")
        import traceback
        traceback.print_exc()

def test_actual_file_processing():
    """Test processing actual files from the bucket using the original parsing logic"""
    logger.info("=== Testing Actual File Processing ===")
    
    try:
        # Import the original processing functions
        from ingest_layer import DataProcessor
        
        storage_client = storage.Client()
        bucket = storage_client.bucket('chess-engine-metrics-agent.firebasestorage.app')
        
        # Get the specific PGN file we know exists
        test_blob = bucket.blob('analysis_results/v7p3r_games_20250823_230947.pgn')
        
        logger.info(f"Processing: {test_blob.name}")
        logger.info(f"File size: {test_blob.size} bytes")
        logger.info(f"File modified: {test_blob.time_created}")
        
        # Download content
        try:
            content = test_blob.download_as_text(encoding='utf-8')
            logger.info(f"Downloaded content: {len(content)} characters")
            logger.info(f"Content preview: {repr(content[:200])}")
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return
            
        # Test original processing function
        try:
            parsed_data = DataProcessor.process_pgn_file(content, test_blob.name)
            logger.info(f"Parsing result: {len(parsed_data) if parsed_data else 0} records")
            
            if parsed_data:
                logger.info("Sample parsed record:")
                sample = parsed_data[0]
                for key, value in sample.items():
                    logger.info(f"  {key}: {repr(value)} ({type(value).__name__})")
                    
                # Test BigQuery insertion of parsed data
                logger.info("Testing BigQuery insertion of parsed data...")
                
                df = pd.DataFrame(parsed_data)
                table_id = 'chess-engine-metrics-agent.chess_engine_data_lake.pgn_games'
                
                client = bigquery.Client(project='chess-engine-metrics-agent')
                job_config = bigquery.LoadJobConfig(write_disposition='WRITE_APPEND')
                
                job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
                job.result()
                
                logger.info("SUCCESS: Parsed data inserted into BigQuery!")
                
            else:
                logger.warning("No data was parsed from the file")
                
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        logger.error(f"File processing test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("Starting BigQuery insertion debug session...")
    
    try:
        # Test BigQuery insertion with known good data
        test_bigquery_insertion()
        
        # Test actual file processing
        test_actual_file_processing()
        
        logger.info("Insertion debug session completed")
        
    except Exception as e:
        logger.error(f"Debug session failed: {e}")
        import traceback
        traceback.print_exc()