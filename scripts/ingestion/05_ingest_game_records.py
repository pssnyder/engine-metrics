#!/usr/bin/env python3
"""
05_ingest_game_records.py

Ingest chess game records (PGN files) from GCS to BigQuery.

Sources:
- Lichess bot games (V7P3R Bot, C0BR4 Bot, SlowMate Bot)
- Engine battle tournaments
- Human vs V7P3R games

This script:
1. Downloads PGN files from gs://v7p3r-raw-data/game_records/
2. Parses each game using python-chess library
3. Extracts metadata, player info, and moves
4. Loads to BigQuery conformed_layer.game_records table
"""

import argparse
import hashlib
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import chess.pgn
from google.cloud import bigquery, storage
from io import StringIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
PROJECT_ID = "chess-engine-metrics-agent"
DATASET_ID = "conformed_layer"
TABLE_ID = "game_records"
GCS_BUCKET = "v7p3r-raw-data"
GCS_PREFIX = "game_records/"

# V7P3R bot names (case-insensitive matching)
V7P3R_BOT_NAMES = {
    'v7p3r',
    'v7p3r_bot',
    'v7p3r-bot',
    'joshsbot',  # User's lichess bot account
}


def generate_game_id(game_data: Dict[str, Any], file_path: str) -> str:
    """
    Generate unique game ID.
    Use Lichess GameId if available, otherwise hash file_path + white + black + date.
    """
    if 'GameId' in game_data and game_data['GameId']:
        return game_data['GameId']
    
    # For local games without GameId, create hash
    hash_input = f"{file_path}_{game_data.get('White')}_{game_data.get('Black')}_{game_data.get('Date')}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def is_v7p3r_player(player_name: str) -> bool:
    """Check if player name belongs to V7P3R bot."""
    if not player_name:
        return False
    return player_name.lower() in V7P3R_BOT_NAMES


def parse_result_for_v7p3r(result: str, v7p3r_color: str) -> Optional[str]:
    """
    Determine V7P3R game outcome.
    
    Args:
        result: PGN result ('1-0', '0-1', '1/2-1/2', '*')
        v7p3r_color: 'white' or 'black'
    
    Returns:
        'win', 'loss', 'draw', or None
    """
    if result == '1/2-1/2':
        return 'draw'
    elif result == '*':
        return None  # Ongoing/abandoned
    elif result == '1-0':
        return 'win' if v7p3r_color == 'white' else 'loss'
    elif result == '0-1':
        return 'win' if v7p3r_color == 'black' else 'loss'
    return None


def extract_version_from_filename(filename: str) -> Optional[str]:
    """Extract V7P3R version from filename if present."""
    import re
    
    # Pattern: v10.2, v14_3, etc.
    patterns = [
        r'v(\d+\.\d+)',      # v10.2
        r'v(\d+_\d+)',       # v14_3
        r'V7P3R[_\s]+v?(\d+\.\d+)',  # V7P3R v10.2 or V7P3R_10.2
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            version = match.group(1).replace('_', '.')
            return f"v{version}"
    
    return None


def parse_pgn_game(game: chess.pgn.Game, file_path: str, file_name: str, game_source: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single PGN game into BigQuery record format.
    
    Args:
        game: chess.pgn.Game object
        file_path: GCS path to source file
        file_name: Source filename
        game_source: Source folder name
    
    Returns:
        Dict ready for BigQuery insertion, or None if invalid game
    """
    try:
        headers = game.headers
        
        # Required fields
        white_player = headers.get('White', 'Unknown')
        black_player = headers.get('Black', 'Unknown')
        result = headers.get('Result', '*')
        
        if not white_player or not black_player:
            logger.warning(f"Skipping game with missing players in {file_name}")
            return None
        
        # Check if V7P3R played
        v7p3r_played = is_v7p3r_player(white_player) or is_v7p3r_player(black_player)
        v7p3r_color = None
        v7p3r_result = None
        opponent_name = None
        opponent_elo = None
        
        if v7p3r_played:
            if is_v7p3r_player(white_player):
                v7p3r_color = 'white'
                opponent_name = black_player
                opponent_elo = int(headers.get('BlackElo', 0)) if headers.get('BlackElo') else None
            else:
                v7p3r_color = 'black'
                opponent_name = white_player
                opponent_elo = int(headers.get('WhiteElo', 0)) if headers.get('WhiteElo') else None
            
            v7p3r_result = parse_result_for_v7p3r(result, v7p3r_color)
        
        # Extract moves
        moves_san = []
        moves_uci = []
        board = game.board()
        
        for move in game.mainline_moves():
            moves_san.append(board.san(move))
            moves_uci.append(move.uci())
            board.push(move)
        
        move_count = len(moves_san)
        opening_moves = ' '.join(moves_san[:10]) if moves_san else None
        
        # Parse date and time
        game_date = None
        game_time = None
        
        date_str = headers.get('UTCDate') or headers.get('Date')
        if date_str:
            try:
                # Parse YYYY.MM.DD format
                game_date = date_str.replace('.', '-')
            except:
                logger.warning(f"Could not parse date: {date_str}")
        
        time_str = headers.get('UTCTime')
        if time_str:
            try:
                # Time is already in HH:MM:SS format
                game_time = time_str
            except:
                logger.warning(f"Could not parse time: {time_str}")
        
        # Extract version from filename or headers
        engine_version = extract_version_from_filename(file_name)
        if not engine_version and 'Version' in headers:
            engine_version = headers.get('Version')
        
        # Build record
        record = {
            'game_id': generate_game_id(headers, file_path),
            'event': headers.get('Event'),
            'site': headers.get('Site'),
            'game_date': game_date,
            'game_time': game_time,
            'time_control': headers.get('TimeControl'),
            'variant': headers.get('Variant'),
            'eco': headers.get('ECO'),
            'result': result,
            'termination': headers.get('Termination'),
            'white_player': white_player,
            'white_elo': int(headers.get('WhiteElo', 0)) if headers.get('WhiteElo') else None,
            'white_rating_diff': int(headers.get('WhiteRatingDiff', 0)) if headers.get('WhiteRatingDiff') else None,
            'white_title': headers.get('WhiteTitle'),
            'black_player': black_player,
            'black_elo': int(headers.get('BlackElo', 0)) if headers.get('BlackElo') else None,
            'black_rating_diff': int(headers.get('BlackRatingDiff', 0)) if headers.get('BlackRatingDiff') else None,
            'black_title': headers.get('BlackTitle'),
            'v7p3r_played': v7p3r_played,
            'v7p3r_color': v7p3r_color,
            'v7p3r_result': v7p3r_result,
            'opponent_name': opponent_name,
            'opponent_elo': opponent_elo,
            'engine_version': engine_version,
            'move_count': move_count,
            'moves_san': ' '.join(moves_san) if moves_san else None,
            'moves_uci': ' '.join(moves_uci) if moves_uci else None,
            'opening_moves': opening_moves,
            'game_source': game_source,
            'file_path': file_path,
            'file_name': file_name,
            'ingested_at': datetime.utcnow().isoformat(),
        }
        
        return record
    
    except Exception as e:
        logger.error(f"Error parsing game from {file_name}: {e}")
        return None


def fetch_pgn_files(storage_client: storage.Client, folder: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch and parse PGN files from GCS.
    
    Args:
        storage_client: GCS client
        folder: Optional subfolder filter (e.g., 'Lichess SlowMate Bot')
        limit: Optional limit on total games to parse
    
    Returns:
        List of parsed game records
    """
    bucket = storage_client.bucket(GCS_BUCKET)
    
    # Determine prefix
    if folder:
        prefix = f"{GCS_PREFIX}{folder}/"
    else:
        prefix = GCS_PREFIX
    
    blobs = bucket.list_blobs(prefix=prefix)
    
    records = []
    games_parsed = 0
    
    for blob in blobs:
        if not blob.name.endswith('.pgn'):
            continue
        
        # Extract game_source from path
        # Path format: game_records/Lichess V7P3R Bot/filename.pgn
        path_parts = blob.name.split('/')
        if len(path_parts) >= 2:
            game_source = path_parts[1]
        else:
            game_source = 'unknown'
        
        file_name = path_parts[-1]
        
        logger.info(f"Fetching {blob.name}")
        
        try:
            # Download PGN content
            content = blob.download_as_text()
            
            # Parse multiple games from file
            pgn_io = StringIO(content)
            
            while True:
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    break  # No more games in file
                
                record = parse_pgn_game(game, blob.name, file_name, game_source)
                if record:
                    records.append(record)
                    games_parsed += 1
                    
                    if limit and games_parsed >= limit:
                        logger.info(f"Reached limit of {limit} games")
                        return records
        
        except Exception as e:
            logger.error(f"Error processing {blob.name}: {e}")
            continue
    
    logger.info(f"Fetched {games_parsed} games from {len(records)} files")
    return records


def create_table_if_not_exists(bq_client: bigquery.Client):
    """Create game_records table if it doesn't exist."""
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    
    try:
        bq_client.get_table(table_ref)
        logger.info(f"Table {table_ref} exists")
        return
    except Exception:
        logger.info(f"Table {table_ref} does not exist, creating...")
    
    schema = [
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("event", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("site", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("game_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("game_time", "TIME", mode="NULLABLE"),
        bigquery.SchemaField("time_control", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("variant", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("eco", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("result", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("termination", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("white_player", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("white_elo", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("white_rating_diff", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("white_title", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("black_player", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("black_elo", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("black_rating_diff", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("black_title", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("v7p3r_played", "BOOLEAN", mode="REQUIRED"),
        bigquery.SchemaField("v7p3r_color", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("v7p3r_result", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("opponent_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("opponent_elo", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("engine_version", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("move_count", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("moves_san", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("moves_uci", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("opening_moves", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("game_source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("file_path", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("file_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="NULLABLE"),
    ]
    
    table = bigquery.Table(table_ref, schema=schema)
    table = bq_client.create_table(table)
    logger.info(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")


def ingest_game_records(dry_run: bool = False, folder: Optional[str] = None, limit: Optional[int] = None):
    """
    Main ingestion function.
    
    Args:
        dry_run: If True, parse and display records without inserting to BigQuery
        folder: Optional subfolder to process (e.g., 'Lichess SlowMate Bot')
        limit: Optional limit on total games to ingest
    """
    logger.info("Starting game records ingestion")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    if folder:
        logger.info(f"Folder filter: {folder}")
    if limit:
        logger.info(f"Limit: {limit} games")
    
    # Initialize clients
    storage_client = storage.Client(project=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID)
    
    # Create table if needed
    create_table_if_not_exists(bq_client)
    
    # Fetch and parse PGN files
    records = fetch_pgn_files(storage_client, folder=folder, limit=limit)
    
    if not records:
        logger.warning("No games found to ingest")
        return
    
    logger.info(f"Parsed {len(records)} games")
    
    # Show sample
    if records:
        sample = records[0]
        logger.info(f"Sample game: {sample['white_player']} vs {sample['black_player']}, "
                   f"Result: {sample['result']}, Moves: {sample['move_count']}, "
                   f"V7P3R played: {sample['v7p3r_played']}")
    
    if dry_run:
        logger.info("DRY RUN - Not inserting to BigQuery")
        logger.info(f"Would insert {len(records)} games")
        return
    
    # Insert to BigQuery using load_table_from_json
    table = bq_client.get_table(f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}")
    
    logger.info(f"Inserting {len(records)} games to BigQuery using load_table_from_json...")
    
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    
    load_job = bq_client.load_table_from_json(records, table, job_config=job_config)
    
    logger.info("Waiting for load job to complete...")
    load_job.result()  # Wait for job to complete
    
    logger.info(f"✅ Successfully ingested {len(records)} games")
    
    # Verify ingestion
    logger.info("Verifying ingestion:")
    query = f"""
    SELECT 
        game_source,
        COUNT(*) as game_count,
        COUNT(DISTINCT engine_version) as version_count,
        SUM(CASE WHEN v7p3r_played THEN 1 ELSE 0 END) as v7p3r_games,
        SUM(CASE WHEN v7p3r_result = 'win' THEN 1 ELSE 0 END) as v7p3r_wins,
        SUM(CASE WHEN v7p3r_result = 'loss' THEN 1 ELSE 0 END) as v7p3r_losses,
        SUM(CASE WHEN v7p3r_result = 'draw' THEN 1 ELSE 0 END) as v7p3r_draws
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    GROUP BY game_source
    ORDER BY game_count DESC
    """
    
    results = bq_client.query(query).result()
    for row in results:
        logger.info(f"  {row.game_source}: {row.game_count} games, "
                   f"V7P3R: {row.v7p3r_games} games ({row.v7p3r_wins}W-{row.v7p3r_losses}L-{row.v7p3r_draws}D)")


def main():
    parser = argparse.ArgumentParser(description='Ingest V7P3R game records to BigQuery')
    parser.add_argument('--dry-run', action='store_true', help='Parse files without inserting to BigQuery')
    parser.add_argument('--folder', type=str, help='Process only this subfolder (e.g., "Lichess SlowMate Bot")')
    parser.add_argument('--limit', type=int, help='Limit number of games to process (for testing)')
    
    args = parser.parse_args()
    
    try:
        ingest_game_records(dry_run=args.dry_run, folder=args.folder, limit=args.limit)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
