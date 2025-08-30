"""
PGN file processor for chess engine tournament data.
"""

import os
import hashlib
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import chardet
import chess.pgn
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Game, ProcessingLog, async_session

logger = logging.getLogger(__name__)

class PGNProcessor:
    """Processes PGN files and stores game data in the database."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.async_session = async_session
        self.data_dirs = config.get('directories', {}).get('data', [])
        
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file for duplicate detection."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return f"error_{time.time()}"
        return hash_md5.hexdigest()
    
    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding using chardet."""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB for detection
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                confidence = result.get('confidence', 0)
                
                logger.debug(f"Detected encoding for {file_path}: {encoding} (confidence: {confidence})")
                
                # Fallback to utf-8 if confidence is too low
                if confidence < 0.7:
                    logger.warning(f"Low confidence encoding detection for {file_path}, using utf-8")
                    return 'utf-8'
                    
                return encoding or 'utf-8'
                
        except Exception as e:
            logger.error(f"Error detecting encoding for {file_path}: {e}")
            return 'utf-8'
    
    def _extract_engine_info(self, game) -> Dict[str, str]:
        """Extract engine information from PGN headers."""
        white_engine = game.headers.get('White', '').lower()
        black_engine = game.headers.get('Black', '').lower()
        
        # Extract engine names (remove version numbers for grouping)
        white_base = white_engine.split('_')[0] if '_' in white_engine else white_engine
        black_base = black_engine.split('_')[0] if '_' in black_engine else black_engine
        
        return {
            'white_engine': white_engine,
            'black_engine': black_engine,
            'white_base': white_base,
            'black_base': black_base
        }
    
    def _is_target_game(self, engine_info: Dict[str, str]) -> bool:
        """Check if game involves target engines."""
        target_engines = self.config.get('engines', {}).get('target_engines', ['v7p3r', 'slowmate'])
        
        white_base = engine_info['white_base']
        black_base = engine_info['black_base']
        
        # Check if both engines are in target list
        white_match = any(target.lower() in white_base for target in target_engines)
        black_match = any(target.lower() in black_base for target in target_engines)
        
        return white_match and black_match
    
    async def _file_already_processed(self, file_path: str, file_hash: str) -> bool:
        """Check if file has already been processed."""
        try:
            async with self.async_session() as session:
                stmt = select(ProcessingLog).where(
                    (ProcessingLog.file_path == file_path) |
                    (ProcessingLog.file_hash == file_hash)
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                return existing is not None
                
        except Exception as e:
            logger.error(f"Error checking if file processed: {e}")
            return False
    
    async def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single PGN file."""
        start_time = time.time()
        games_processed = 0
        games_stored = 0
        
        try:
            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)
            
            # Check if already processed
            if await self._file_already_processed(file_path, file_hash):
                logger.info(f"File already processed: {file_path}")
                return {
                    'file_path': file_path,
                    'status': 'skipped',
                    'reason': 'already_processed',
                    'games_processed': 0,
                    'games_stored': 0,
                    'processing_time': time.time() - start_time
                }
            
            # Detect encoding
            encoding = self._detect_encoding(file_path)
            
            # Process games
            games_to_store = []
            
            try:
                with open(file_path, 'r', encoding=encoding, errors='replace') as pgn_file:
                    while True:
                        game = chess.pgn.read_game(pgn_file)
                        if game is None:
                            break
                            
                        games_processed += 1
                        
                        # Extract engine information
                        engine_info = self._extract_engine_info(game)
                        
                        # Check if this is a target game
                        if not self._is_target_game(engine_info):
                            continue
                        
                        # Extract game data
                        game_data = self._extract_game_data(game, engine_info, file_path)
                        games_to_store.append(game_data)
                        
            except Exception as e:
                logger.error(f"Error reading PGN file {file_path}: {e}")
                return {
                    'file_path': file_path,
                    'status': 'error',
                    'error': str(e),
                    'games_processed': games_processed,
                    'games_stored': 0,
                    'processing_time': time.time() - start_time
                }
            
            # Store games in database
            if games_to_store:
                games_stored = await self._store_games(games_to_store)
            
            # Log processing
            await self._log_processing(file_path, file_hash, games_processed, games_stored)
            
            logger.info(f"Processed {file_path}: {games_processed} games, {games_stored} stored")
            
            return {
                'file_path': file_path,
                'status': 'success',
                'games_processed': games_processed,
                'games_stored': games_stored,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return {
                'file_path': file_path,
                'status': 'error',
                'error': str(e),
                'games_processed': games_processed,
                'games_stored': games_stored,
                'processing_time': time.time() - start_time
            }
    
    def _extract_game_data(self, game, engine_info: Dict[str, str], file_path: str) -> Dict[str, Any]:
        """Extract game data for database storage."""
        headers = game.headers
        
        # Parse date
        game_date = None
        if 'Date' in headers and headers['Date'] != '????.??.??':
            try:
                # Handle various date formats
                date_str = headers['Date'].replace('?', '01')
                if '.' in date_str:
                    game_date = datetime.strptime(date_str, '%Y.%m.%d').date()
                elif '-' in date_str:
                    game_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError as e:
                logger.warning(f"Could not parse date '{headers['Date']}': {e}")
        
        # Determine result
        result = headers.get('Result', '*')
        if result == '1-0':
            winner = 'white'
        elif result == '0-1':
            winner = 'black'
        else:
            winner = 'draw'
        
        return {
            'white_engine': engine_info['white_engine'],
            'black_engine': engine_info['black_engine'],
            'white_base': engine_info['white_base'],
            'black_base': engine_info['black_base'],
            'result': result,
            'winner': winner,
            'game_date': game_date,
            'event': headers.get('Event', ''),
            'round': headers.get('Round', ''),
            'plycount': int(headers.get('PlyCount', 0)) if headers.get('PlyCount', '').isdigit() else 0,
            'time_control': headers.get('TimeControl', ''),
            'termination': headers.get('Termination', ''),
            'source_file': file_path,
            'pgn_text': str(game)
        }
    
    async def _store_games(self, games_data: List[Dict[str, Any]]) -> int:
        """Store games in the database."""
        stored_count = 0
        
        try:
            async with self.async_session() as session:
                for game_data in games_data:
                    try:
                        game = Game(**game_data)
                        session.add(game)
                        stored_count += 1
                    except Exception as e:
                        logger.error(f"Error creating game object: {e}")
                        continue
                
                await session.commit()
                logger.info(f"Stored {stored_count} games in database")
                
        except Exception as e:
            logger.error(f"Error storing games: {e}")
            
        return stored_count
    
    async def _log_processing(self, file_path: str, file_hash: str, games_processed: int, games_stored: int):
        """Log file processing in the database."""
        try:
            async with self.async_session() as session:
                log_entry = ProcessingLog(
                    file_path=file_path,
                    file_hash=file_hash,
                    games_processed=games_processed,
                    games_stored=games_stored,
                    processed_at=datetime.now()
                )
                
                session.add(log_entry)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error logging processing: {e}")
    
    async def process_batch(self) -> Dict[str, Any]:
        """Process all PGN files in configured directories."""
        start_time = time.time()
        processed_count = 0
        new_count = 0
        skipped_count = 0
        total_games = 0
        
        try:
            for data_dir in self.data_dirs:
                if not os.path.exists(data_dir):
                    logger.warning(f"Data directory does not exist: {data_dir}")
                    continue
                
                logger.info(f"Processing directory: {data_dir}")
                
                for root, dirs, files in os.walk(data_dir):
                    for file in files:
                        if file.lower().endswith('.pgn'):
                            file_path = os.path.join(root, file)
                            
                            result = await self.process_file(file_path)
                            processed_count += 1
                            
                            if result['status'] == 'success':
                                new_count += 1
                                total_games += result['games_stored']
                            elif result['status'] == 'skipped':
                                skipped_count += 1
                            
                            # Log progress
                            if processed_count % 10 == 0:
                                logger.info(f"Processed {processed_count} files so far...")
            
            logger.info(f"Batch processing complete: {processed_count} files, {new_count} new, {skipped_count} skipped, {total_games} games")
            
            return {
                'total_processed': processed_count,
                'new_files': new_count,
                'skipped_files': skipped_count,
                'total_games': total_games,
                'processing_time': time.time() - start_time,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return {
                'total_processed': processed_count,
                'new_files': new_count,
                'skipped_files': skipped_count,
                'total_games': total_games,
                'processing_time': time.time() - start_time,
                'success': False,
                'error': str(e)
            }
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics from the database."""
        try:
            async with self.async_session() as session:
                # Get total files processed
                total_files_stmt = select(func.count(ProcessingLog.id))
                total_files_result = await session.execute(total_files_stmt)
                total_files = total_files_result.scalar()
                
                # Get total games
                total_games_stmt = select(func.count(Game.id))
                total_games_result = await session.execute(total_games_stmt)
                total_games = total_games_result.scalar()
                
                # Get recent processing (last 24 hours)
                since = datetime.now() - timedelta(hours=24)
                recent_files_stmt = select(func.count(ProcessingLog.id)).where(
                    ProcessingLog.processed_at > since
                )
                recent_files_result = await session.execute(recent_files_stmt)
                recent_files = recent_files_result.scalar()
                
                # Get latest processing timestamp
                latest_stmt = select(ProcessingLog.processed_at).order_by(
                    ProcessingLog.processed_at.desc()
                ).limit(1)
                latest_result = await session.execute(latest_stmt)
                latest_processing = latest_result.scalar_one_or_none()
                
                return {
                    'total_files_processed': total_files or 0,
                    'total_games': total_games or 0,
                    'recent_files_24h': recent_files or 0,
                    'latest_processing': latest_processing.isoformat() if latest_processing else None,
                    'status': 'operational'
                }
                
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {
                'total_files_processed': 0,
                'total_games': 0,
                'recent_files_24h': 0,
                'latest_processing': None,
                'status': 'error',
                'error': str(e)
            }
