#!/usr/bin/env python3
"""
Debug script to test file parsing and identify issues with Unicode and schema matching
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Any
import logging

# Setup basic logging without Unicode issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_parsing.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def safe_read_file(file_path: str) -> str:
    """Safely read a file with proper Unicode handling"""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            logger.info(f"Successfully read file with {encoding} encoding")
            return content
        except UnicodeDecodeError:
            logger.warning(f"Failed to read with {encoding} encoding")
            continue
        except Exception as e:
            logger.error(f"Error reading file with {encoding}: {e}")
            continue
    
    # Fallback: read as binary and decode with error handling
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        decoded = content.decode('utf-8', errors='replace')
        logger.info("Read file using binary mode with error replacement")
        return decoded
    except Exception as e:
        logger.error(f"Failed to read file even with fallback method: {e}")
        return ""

def test_pgn_parsing():
    """Test PGN file parsing with proper Unicode handling"""
    from google.cloud import storage
    
    logger.info("=== Testing PGN File Parsing ===")
    
    # Initialize storage client
    try:
        client = storage.Client()
        bucket = client.bucket('chess-engine-metrics-agent.firebasestorage.app')
        
        # Find PGN files
        pgn_files = []
        for blob in bucket.list_blobs():
            if blob.name.endswith('.pgn') and not blob.name.endswith('/'):
                pgn_files.append(blob)
                
        logger.info(f"Found {len(pgn_files)} PGN files")
        
        if not pgn_files:
            logger.warning("No PGN files found in bucket")
            return
            
        # Test first PGN file
        test_blob = pgn_files[0]
        logger.info(f"Testing file: {test_blob.name}")
        
        # Download and parse
        try:
            content = test_blob.download_as_text(encoding='utf-8')
            logger.info(f"Downloaded {len(content)} characters")
        except UnicodeDecodeError:
            logger.warning("UTF-8 decode failed, trying latin-1")
            try:
                content = test_blob.download_as_text(encoding='latin-1')
                logger.info(f"Downloaded {len(content)} characters with latin-1")
            except Exception as e:
                logger.error(f"Failed to download file: {e}")
                return
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return
            
        # Test parsing with python-chess
        try:
            import chess.pgn
            from io import StringIO
            
            games = []
            pgn_io = StringIO(content)
            
            game_count = 0
            while True:
                try:
                    game = chess.pgn.read_game(pgn_io)
                    if game is None:
                        break
                    games.append(game)
                    game_count += 1
                    if game_count >= 3:  # Test first 3 games
                        break
                except Exception as e:
                    logger.error(f"Error parsing game {game_count + 1}: {e}")
                    break
                    
            logger.info(f"Successfully parsed {len(games)} games")
            
            # Test data extraction
            if games:
                test_game = games[0]
                logger.info("Testing data extraction from first game:")
                
                # Extract headers
                headers = dict(test_game.headers)
                logger.info(f"Headers: {list(headers.keys())}")
                
                # Test date parsing
                date_str = headers.get('Date', '????.??.??')
                logger.info(f"Date string: '{date_str}'")
                
                # Test moves
                moves = []
                board = test_game.board()
                for move in test_game.mainline_moves():
                    moves.append(board.san(move))
                    board.push(move)
                    
                logger.info(f"Moves: {' '.join(moves[:10])}{'...' if len(moves) > 10 else ''}")
                
                # Create sample record like BigQuery expects
                sample_record = {
                    'game_id': f"{headers.get('Event', 'Unknown')}_{headers.get('Round', '1')}_{game_count}",
                    'event': headers.get('Event', 'Unknown Event'),
                    'site': headers.get('Site', 'Unknown Site'),
                    'date': None,  # We'll handle this separately
                    'round': headers.get('Round', '1'),
                    'white': headers.get('White', 'Unknown White'),
                    'black': headers.get('Black', 'Unknown Black'),
                    'result': headers.get('Result', '*'),
                    'white_elo': None,
                    'black_elo': None,
                    'time_control': headers.get('TimeControl'),
                    'opening': headers.get('Opening'),
                    'moves': ' '.join(moves),
                    'move_count': len(moves),
                    'game_duration': None,
                    'termination': headers.get('Termination'),
                    'source_file': test_blob.name,
                    'ingested_at': datetime.now(),
                    'file_modified_at': test_blob.time_created
                }
                
                logger.info("Sample record created successfully")
                logger.info(f"Record keys: {list(sample_record.keys())}")
                
                # Test date parsing specifically
                try:
                    if date_str and date_str != '????.??.??':
                        # Common PGN date formats
                        date_formats = ['%Y.%m.%d', '%Y-%m-%d', '%Y/%m/%d']
                        parsed_date = None
                        
                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                continue
                                
                        if parsed_date:
                            sample_record['date'] = parsed_date
                            logger.info(f"Parsed date: {parsed_date}")
                        else:
                            logger.warning(f"Could not parse date: {date_str}")
                    
                except Exception as e:
                    logger.error(f"Date parsing error: {e}")
                    
                return sample_record
                
        except ImportError:
            logger.error("python-chess not available for testing")
        except Exception as e:
            logger.error(f"PGN parsing error: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        logger.error(f"Storage access error: {e}")
        import traceback
        traceback.print_exc()

def test_json_parsing():
    """Test JSON analysis file parsing"""
    from google.cloud import storage
    
    logger.info("=== Testing JSON File Parsing ===")
    
    try:
        client = storage.Client()
        bucket = client.bucket('chess-engine-metrics-agent.firebasestorage.app')
        
        # Find JSON files
        json_files = []
        for blob in bucket.list_blobs():
            if blob.name.endswith('.json') and not blob.name.endswith('/'):
                json_files.append(blob)
                if len(json_files) >= 3:  # Test first 3
                    break
                    
        logger.info(f"Found {len(json_files)} JSON files")
        
        for i, test_blob in enumerate(json_files):
            logger.info(f"\nTesting JSON file {i+1}: {test_blob.name}")
            
            try:
                content = test_blob.download_as_text(encoding='utf-8')
                logger.info(f"Downloaded {len(content)} characters")
                
                # Parse JSON
                data = json.loads(content)
                logger.info(f"JSON structure: {type(data)} with {len(data) if isinstance(data, (list, dict)) else 'N/A'} items")
                
                if isinstance(data, dict):
                    logger.info(f"JSON keys: {list(data.keys())[:10]}")
                elif isinstance(data, list) and len(data) > 0:
                    logger.info(f"First item type: {type(data[0])}")
                    if isinstance(data[0], dict):
                        logger.info(f"First item keys: {list(data[0].keys())[:10]}")
                        
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
            except Exception as e:
                logger.error(f"Error processing JSON file: {e}")
                
    except Exception as e:
        logger.error(f"Storage access error: {e}")

def test_markdown_parsing():
    """Test Markdown documentation file parsing"""
    from google.cloud import storage
    
    logger.info("=== Testing Markdown File Parsing ===")
    
    try:
        client = storage.Client()
        bucket = client.bucket('chess-engine-metrics-agent.firebasestorage.app')
        
        # Find markdown files
        md_files = []
        for blob in bucket.list_blobs():
            if blob.name.endswith('.md') and not blob.name.endswith('/'):
                md_files.append(blob)
                if len(md_files) >= 3:  # Test first 3
                    break
                    
        logger.info(f"Found {len(md_files)} Markdown files")
        
        for i, test_blob in enumerate(md_files):
            logger.info(f"\nTesting Markdown file {i+1}: {test_blob.name}")
            
            try:
                content = test_blob.download_as_text(encoding='utf-8')
                logger.info(f"Downloaded {len(content)} characters")
                logger.info(f"First 200 characters: {repr(content[:200])}")
                
                # Create sample documentation record
                sample_record = {
                    'doc_id': f"doc_{hash(test_blob.name) % 1000000}",
                    'title': os.path.basename(test_blob.name).replace('.md', '').replace('_', ' ').title(),
                    'content': content[:10000],  # Truncate for BigQuery
                    'doc_type': 'markdown',
                    'engine_version': 'unknown',  # Would extract from filename/content
                    'source_file': test_blob.name,
                    'ingested_at': datetime.now(),
                    'file_modified_at': test_blob.time_created
                }
                
                logger.info("Markdown record created successfully")
                
            except UnicodeDecodeError as e:
                logger.error(f"Unicode error in markdown: {e}")
                try:
                    content = test_blob.download_as_text(encoding='latin-1')
                    logger.info(f"Successfully read with latin-1: {len(content)} characters")
                except Exception as e2:
                    logger.error(f"Failed with latin-1: {e2}")
            except Exception as e:
                logger.error(f"Error processing markdown file: {e}")
                
    except Exception as e:
        logger.error(f"Storage access error: {e}")

if __name__ == "__main__":
    logger.info("Starting file parsing debug session...")
    
    try:
        # Test each file type
        test_pgn_parsing()
        test_json_parsing() 
        test_markdown_parsing()
        
        logger.info("Debug session completed")
        
    except Exception as e:
        logger.error(f"Debug session failed: {e}")
        import traceback
        traceback.print_exc()