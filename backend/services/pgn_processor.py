import os
import chess.pgn
import chess
import chardet
import hashlib
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import Game, ProcessingLog, SessionLocal

logger = logging.getLogger(__name__)

class PGNProcessor:
    """Handles processing of PGN files and extraction of game data."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.encoding_fallbacks = config.get('processing', {}).get('encoding_fallbacks', 
                                                                  ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1'])
        self.target_engines = [name.lower() for name in config.get('engines', {}).get('target_engines', [])]
        self.version_pattern = config.get('engines', {}).get('version_pattern', r'v\d+\.\d+')
        
    def detect_encoding(self, file_path: str) -> str:
        """Detect file encoding using multiple methods."""
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read()
                result = chardet.detect(raw_data)
                if result and result['confidence'] > 0.7:
                    return result['encoding']
        except Exception as e:
            logger.warning(f"Encoding detection failed for {file_path}: {e}")
        
        # Fallback to trying encodings in order
        for encoding in self.encoding_fallbacks:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    file.read(1024)  # Try to read a small portion
                    return encoding
            except UnicodeDecodeError:
                continue
        
        logger.warning(f"Could not determine encoding for {file_path}, using utf-8 with error handling")
        return 'utf-8'
    
    def read_pgn_file(self, file_path: str) -> Tuple[str, str]:
        """Read PGN file content with encoding handling."""
        encoding = self.detect_encoding(file_path)
        
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read()
                return content, encoding
        except UnicodeDecodeError:
            # Last resort: read with error handling
            with open(file_path, 'r', encoding=encoding, errors='replace') as file:
                content = file.read()
                logger.warning(f"Used error replacement while reading {file_path}")
                return content, f"{encoding}_with_errors"
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate hash of file for duplicate detection."""
        hash_obj = hashlib.md5()
        try:
            with open(file_path, 'rb') as file:
                for chunk in iter(lambda: file.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return f"error_{os.path.getmtime(file_path)}"
    
    def is_target_engine_game(self, white_player: str, black_player: str) -> bool:
        """Check if game involves target engines (v7p3r vs slowmate)."""
        white_clean = white_player.lower() if white_player else ""
        black_clean = black_player.lower() if black_player else ""
        
        # Check if both players are target engines with versions
        white_match = any(engine in white_clean for engine in self.target_engines) and \
                     bool(re.search(self.version_pattern, white_clean))
        black_match = any(engine in black_clean for engine in self.target_engines) and \
                     bool(re.search(self.version_pattern, black_clean))
        
        return white_match and black_match
    
    def extract_engine_version(self, player_name: str) -> Optional[str]:
        """Extract engine version from player name."""
        if not player_name:
            return None
        
        match = re.search(self.version_pattern, player_name.lower())
        return match.group(0) if match else None
    
    def calculate_material_value(self, board: chess.Board) -> float:
        """Calculate material value for position (in pawn equivalents)."""
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0
        }
        
        white_material = sum(piece_values[piece.piece_type] 
                           for piece in board.piece_map().values() 
                           if piece.color == chess.WHITE)
        black_material = sum(piece_values[piece.piece_type] 
                           for piece in board.piece_map().values() 
                           if piece.color == chess.BLACK)
        
        return white_material - black_material
    
    def classify_game_outcome(self, game_data: Dict[str, Any], board: chess.Board) -> Dict[str, Any]:
        """Classify game outcome based on custom criteria."""
        result = game_data.get('result', '')
        termination = game_data.get('termination', '').lower()
        final_material_diff = game_data.get('final_material_difference', 0)
        max_white_advantage = game_data.get('max_white_advantage', 0)
        max_black_advantage = game_data.get('max_black_advantage', 0)
        
        classification = {
            'is_decisive_win': False,
            'is_soft_loss': False,
            'is_missed_win': False,
            'classification_reason': ''
        }
        
        material_threshold = self.config.get('metrics', {}).get('material_advantage_threshold', 3)
        
        # Decisive wins: checkmates and resignations by material advantage
        if 'mate' in termination or 'checkmate' in termination:
            classification['is_decisive_win'] = True
            classification['classification_reason'] = 'Checkmate'
        elif 'resign' in termination and abs(final_material_diff) >= material_threshold:
            classification['is_decisive_win'] = True
            classification['classification_reason'] = f'Resignation with material advantage ({final_material_diff:.1f})'
        
        # Soft losses: losses by adjudication or other non-mate factors
        elif result in ['0-1', '1-0'] and 'mate' not in termination:
            if 'time' in termination or 'adjudication' in termination or 'illegal' in termination:
                classification['is_soft_loss'] = True
                classification['classification_reason'] = f'Loss by {termination}'
        
        # Missed wins: draws/losses with material advantage
        if result == '1/2-1/2':  # Draw
            if max_white_advantage >= material_threshold or max_black_advantage >= material_threshold:
                classification['is_missed_win'] = True
                max_adv = max(max_white_advantage, max_black_advantage)
                classification['classification_reason'] = f'Draw despite material advantage ({max_adv:.1f})'
        elif result in ['0-1', '1-0']:  # Someone lost
            losing_had_advantage = (result == '0-1' and max_white_advantage >= material_threshold) or \
                                 (result == '1-0' and max_black_advantage >= material_threshold)
            if losing_had_advantage:
                classification['is_missed_win'] = True
                adv = max_white_advantage if result == '0-1' else max_black_advantage
                classification['classification_reason'] = f'Loss despite material advantage ({adv:.1f})'
        
        return classification
    
    def analyze_game_moves(self, pgn_game: chess.pgn.Game) -> Dict[str, Any]:
        """Analyze game moves for time, depth, and material tracking."""
        board = chess.Board()
        
        total_moves = 0
        move_times = {'white': [], 'black': []}
        move_depths = {'white': [], 'black': []}
        material_history = []
        
        max_white_advantage = 0
        max_black_advantage = 0
        
        node = pgn_game
        while node.variations:
            node = node.variation(0)
            board.push(node.move)
            total_moves += 1
            
            # Track material advantage
            material_diff = self.calculate_material_value(board)
            material_history.append(material_diff)
            
            if material_diff > max_white_advantage:
                max_white_advantage = material_diff
            if material_diff < -max_black_advantage:
                max_black_advantage = -material_diff
            
            # Extract time and depth from comments if available
            comment = node.comment
            if comment:
                # Look for time patterns like [%clk 0:05:23] or [%emt 0:00:15]
                time_match = re.search(r'\[%(?:clk|emt)\s+(\d+):(\d+):(\d+)\]', comment)
                if time_match:
                    hours, minutes, seconds = map(int, time_match.groups())
                    move_time = hours * 3600 + minutes * 60 + seconds
                    color = 'white' if board.turn == chess.BLACK else 'black'  # Previous move's color
                    move_times[color].append(move_time)
                
                # Look for depth patterns like [%eval 0.15,15] where 15 is depth
                depth_match = re.search(r'\[%eval\s+[^,]+,(\d+)\]', comment)
                if depth_match:
                    depth = int(depth_match.group(1))
                    color = 'white' if board.turn == chess.BLACK else 'black'
                    move_depths[color].append(depth)
        
        final_material_diff = material_history[-1] if material_history else 0
        
        return {
            'total_moves': total_moves,
            'white_avg_time': sum(move_times['white']) / len(move_times['white']) if move_times['white'] else None,
            'black_avg_time': sum(move_times['black']) / len(move_times['black']) if move_times['black'] else None,
            'white_avg_depth': sum(move_depths['white']) / len(move_depths['white']) if move_depths['white'] else None,
            'black_avg_depth': sum(move_depths['black']) / len(move_depths['black']) if move_depths['black'] else None,
            'final_material_difference': final_material_diff,
            'max_white_advantage': max_white_advantage,
            'max_black_advantage': max_black_advantage
        }
    
    def process_single_game(self, pgn_game: chess.pgn.Game, file_path: str, file_hash: str) -> Optional[Dict[str, Any]]:
        """Process a single game from PGN."""
        headers = pgn_game.headers
        
        white_player = headers.get('White', '')
        black_player = headers.get('Black', '')
        
        # Filter to only target engine games
        if not self.is_target_engine_game(white_player, black_player):
            return None
        
        # Extract basic game data
        game_data = {
            'file_path': file_path,
            'file_hash': file_hash,
            'event': headers.get('Event', ''),
            'site': headers.get('Site', ''),
            'date': headers.get('Date', ''),
            'round': headers.get('Round', ''),
            'white_player': white_player,
            'black_player': black_player,
            'result': headers.get('Result', ''),
            'termination': headers.get('Termination', ''),
            'time_control': headers.get('TimeControl', ''),
            'white_engine_version': self.extract_engine_version(white_player),
            'black_engine_version': self.extract_engine_version(black_player),
            'pgn_content': str(pgn_game)
        }
        
        # Analyze moves for detailed metrics
        move_analysis = self.analyze_game_moves(pgn_game)
        game_data.update(move_analysis)
        
        # Classify the game outcome
        board = chess.Board()
        node = pgn_game
        while node.variations:
            node = node.variation(0)
            board.push(node.move)
        
        classification = self.classify_game_outcome(game_data, board)
        game_data.update(classification)
        
        return game_data
    
    def process_pgn_file(self, file_path: str) -> Dict[str, Any]:
        """Process a complete PGN file."""
        logger.info(f"Processing PGN file: {file_path}")
        
        processing_result = {
            'file_path': file_path,
            'status': 'success',
            'games_processed': 0,
            'error_message': None,
            'encoding_used': None,
            'file_size': 0
        }
        
        try:
            # Calculate file info
            file_hash = self.calculate_file_hash(file_path)
            processing_result['file_size'] = os.path.getsize(file_path)
            
            # Read file content
            content, encoding = self.read_pgn_file(file_path)
            processing_result['encoding_used'] = encoding
            
            # Check if file already processed
            db = SessionLocal()
            try:
                existing_log = db.query(ProcessingLog).filter(
                    ProcessingLog.file_path == file_path,
                    ProcessingLog.status == 'success'
                ).first()
                
                if existing_log:
                    logger.info(f"File {file_path} already processed, skipping")
                    processing_result['status'] = 'skipped'
                    return processing_result
                
                # Process games
                games_data = []
                import io
                pgn_io = io.StringIO(content)
                
                while True:
                    try:
                        game = chess.pgn.read_game(pgn_io)
                        if game is None:
                            break
                        
                        game_data = self.process_single_game(game, file_path, file_hash)
                        if game_data:
                            games_data.append(game_data)
                    
                    except Exception as e:
                        logger.warning(f"Error processing individual game in {file_path}: {e}")
                        continue
                
                # Save games to database
                for game_data in games_data:
                    # Check for duplicates by hash
                    existing_game = db.query(Game).filter(Game.file_hash == game_data['file_hash']).first()
                    if not existing_game:
                        game = Game(**game_data)
                        db.add(game)
                
                processing_result['games_processed'] = len(games_data)
                
                # Log processing
                log_entry = ProcessingLog(
                    file_path=file_path,
                    processing_completed=datetime.utcnow(),
                    status='success',
                    games_processed=len(games_data),
                    file_size=processing_result['file_size'],
                    encoding_used=encoding
                )
                db.add(log_entry)
                
                db.commit()
                logger.info(f"Successfully processed {len(games_data)} games from {file_path}")
                
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            processing_result['status'] = 'error'
            processing_result['error_message'] = str(e)
            
            # Log the error
            db = SessionLocal()
            try:
                log_entry = ProcessingLog(
                    file_path=file_path,
                    processing_completed=datetime.utcnow(),
                    status='error',
                    error_message=str(e),
                    file_size=processing_result.get('file_size', 0),
                    encoding_used=processing_result.get('encoding_used')
                )
                db.add(log_entry)
                db.commit()
            finally:
                db.close()
        
        return processing_result
    
    def file_needs_processing(self, file_path: str) -> bool:
        """Check if a file needs to be processed based on modification time and processing history."""
        if not os.path.exists(file_path):
            return False
        
        try:
            file_stat = os.stat(file_path)
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            file_size = file_stat.st_size
            
            with SessionLocal() as session:
                # Check if file has been processed successfully and hasn't been modified since
                existing_log = session.query(ProcessingLog).filter(
                    and_(
                        ProcessingLog.file_path == file_path,
                        ProcessingLog.status == 'success'
                    )
                ).order_by(ProcessingLog.processing_completed.desc()).first()
                
                if existing_log and existing_log.processing_completed is not None:
                    # Check if file was modified after last successful processing
                    if file_mtime <= existing_log.processing_completed:
                        # Also check file size to catch cases where modification time might be unreliable
                        if hasattr(existing_log, 'file_size') and existing_log.file_size == file_size:
                            logger.debug(f"Skipping {file_path} - already processed successfully and unchanged")
                            return False
                
                return True
                
        except Exception as e:
            logger.warning(f"Error checking processing status for {file_path}: {e}")
            return True  # Process if we can't determine status
    
    def get_processed_files_summary(self) -> Dict[str, Any]:
        """Get summary of processed files to avoid redundant processing."""
        try:
            with SessionLocal() as session:
                total_logs = session.query(ProcessingLog).count()
                successful_logs = session.query(ProcessingLog).filter(ProcessingLog.status == 'success').count()
                error_logs = session.query(ProcessingLog).filter(ProcessingLog.status == 'error').count()
                
                recent_successful = session.query(ProcessingLog).filter(
                    and_(
                        ProcessingLog.status == 'success',
                        ProcessingLog.processing_completed > datetime.now() - timedelta(days=7)
                    )
                ).count()
                
                return {
                    'total_files_logged': total_logs,
                    'successful_files': successful_logs,
                    'error_files': error_logs,
                    'recent_successful_files': recent_successful
                }
        except Exception as e:
            logger.error(f"Error getting processed files summary: {e}")
            return {'error': str(e)}
    
    def process_multiple_files_selective(self, file_paths: List[str], skip_processed: bool = True) -> List[Dict[str, Any]]:
        """Process multiple PGN files with option to skip already processed files."""
        results = []
        skipped_count = 0
        error_summary = {}
        
        for file_path in file_paths:
            if not os.path.exists(file_path) or not file_path.lower().endswith('.pgn'):
                logger.debug(f"Skipping invalid file: {file_path}")
                continue
            
            # Check if we should skip already processed files
            if skip_processed and not self.file_needs_processing(file_path):
                skipped_count += 1
                continue
            
            result = self.process_pgn_file(file_path)
            
            # Aggregate errors to reduce log spam
            if result.get('status') == 'error':
                error_type = result.get('error_message', 'Unknown error')[:50]  # First 50 chars
                if error_type not in error_summary:
                    error_summary[error_type] = 0
                error_summary[error_type] += 1
            
            results.append(result)
        
        # Log summary instead of individual errors
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} already-processed files")
        
        if error_summary:
            logger.warning(f"Processing errors summary: {error_summary}")
        
        return results
    
    def process_multiple_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple PGN files."""
        results = []
        
        for file_path in file_paths:
            if os.path.exists(file_path) and file_path.lower().endswith('.pgn'):
                result = self.process_pgn_file(file_path)
                results.append(result)
            else:
                logger.warning(f"Skipping invalid file: {file_path}")
        
        return results
