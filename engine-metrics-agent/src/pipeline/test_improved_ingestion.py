#!/usr/bin/env python3
"""
Test the improved ingestion with actual files
"""

import json
import logging
from ingest_layer import IngestLayer
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_improved_ingestion():
    """Test ingestion with improved parsing"""
    logger.info("Testing ingestion with improved parsing...")
    
    try:
        # Clear processed files
        with open('processed_files.json', 'w') as f:
            json.dump([], f)
        
        # Initialize ingest layer
        ingest = IngestLayer()
        
        # Get large PGN files
        large_files = []
        for blob in ingest.storage_monitor.scan_for_new_files():
            if blob.name.endswith('.pgn') and blob.size and blob.size > 10000:
                large_files.append(blob)
                if len(large_files) >= 2:  # Test 2 files only
                    break
        
        logger.info(f"Testing {len(large_files)} large PGN files")
        for blob in large_files:
            logger.info(f"  - {blob.name} ({blob.size:,} bytes)")
        
        # Process files
        total_games = 0
        client = bigquery.Client(project='chess-engine-metrics-agent')
        
        for i, blob in enumerate(large_files):
            logger.info(f"Processing file {i+1}: {blob.name}")
            
            try:
                success = ingest.storage_monitor.process_file(blob)
                logger.info(f"Result: {'Success' if success else 'Failed'}")
                
                if success:
                    # Check games added
                    query = f"SELECT COUNT(*) as count FROM chess_engine_data_lake.pgn_games WHERE source_file = '{blob.name}'"
                    result = list(client.query(query).result())[0]
                    games_added = result.count
                    total_games += games_added
                    logger.info(f"Games added: {games_added}")
                    
            except Exception as e:
                logger.error(f"Error processing {blob.name}: {e}")
                import traceback
                traceback.print_exc()
        
        logger.info(f"TOTAL GAMES INGESTED: {total_games}")
        
        # Show sample data
        if total_games > 0:
            query = "SELECT game_id, white, black, result, move_count FROM chess_engine_data_lake.pgn_games ORDER BY ingested_at DESC LIMIT 5"
            logger.info("Sample recent games:")
            for row in client.query(query).result():
                logger.info(f"  {row.game_id}: {row.white} vs {row.black} = {row.result} ({row.move_count} moves)")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_improved_ingestion()