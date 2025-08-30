import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import json

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(__file__))
backend_path = os.path.join(project_root, 'backend')
sys.path.insert(0, project_root)
sys.path.insert(0, backend_path)

# Try importing the required modules
PGNProcessor = None
MetricsCalculator = None
init_db = None

try:
    # Import from backend directory
    import sys
    import os
    
    # Add backend to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    backend_path = os.path.join(project_root, 'backend')
    
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    from backend.services.pgn_processor import PGNProcessor
    from backend.services.metrics_calculator import MetricsCalculator  
    from backend.database.models import init_db
    logger.info("Successfully imported backend modules")
except ImportError as e:
    logger.warning(f"Could not import backend modules: {e}")
    logger.info("ETL will run in test mode without database operations")

# Import SQLAlchemy if available for async operations
try:
    import sqlalchemy
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.warning("SQLAlchemy not available")

class RealTimeETL:
    """Real-time ETL pipeline for tournament data."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.pgn_processor = None
        self.metrics_calculator = None
        self.last_update = None
        self.tournament_cache = {}
        self.running = False
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration."""
        if not config_path:
            config_path = str(Path(__file__).parent.parent / "config" / "settings.yaml")
            
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    async def initialize(self):
        """Initialize the ETL pipeline."""
        try:
            # Check if backend modules are available
            if not all([PGNProcessor, MetricsCalculator, init_db]):
                logger.warning("Backend modules not available - running in test mode")
                return True
                
            # Initialize database
            await init_db()
            
            # Initialize processors
            self.pgn_processor = PGNProcessor(self.config)
            self.metrics_calculator = MetricsCalculator(self.config)
            
            logger.info("Real-time ETL pipeline initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing ETL pipeline: {e}")
            logger.info("Falling back to test mode")
            return True  # Still return True to allow testing
    
    async def process_new_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process a list of new tournament files."""
        try:
            results = {
                'processed_files': 0,
                'new_games': 0,
                'errors': [],
                'tournaments_updated': []
            }
            
            # If no processors available, simulate processing
            if not self.pgn_processor:
                logger.info(f"Test mode: Would process {len(file_paths)} files")
                results['processed_files'] = len(file_paths)
                results['new_games'] = len(file_paths) * 10  # Simulate 10 games per file
                return results
            
            for file_path in file_paths:
                try:
                    file_result = await self._process_single_file(file_path)
                    results['processed_files'] += 1
                    results['new_games'] += file_result.get('new_games', 0)
                    
                    # Track tournament updates
                    tournament_id = self._extract_tournament_id(file_path)
                    if tournament_id not in results['tournaments_updated']:
                        results['tournaments_updated'].append(tournament_id)
                        
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Update metrics if any files were processed
            if results['processed_files'] > 0:
                await self._update_tournament_metrics(results['tournaments_updated'])
            
            self.last_update = datetime.now()
            return results
            
        except Exception as e:
            logger.error(f"Error in process_new_files: {e}")
            return {'error': str(e)}
    
    async def _process_single_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single tournament file."""
        if not self.pgn_processor:
            logger.info(f"Test mode: Would process file {file_path}")
            return {'games_processed': 10}  # Simulate processing
            
        # Process the file
        result = await self.pgn_processor.process_file(file_path)
        
        # Update tournament cache
        tournament_id = self._extract_tournament_id(file_path)
        if tournament_id not in self.tournament_cache:
            self.tournament_cache[tournament_id] = {
                'id': tournament_id,
                'start_time': datetime.now(),
                'last_update': datetime.now(),
                'files_processed': 0,
                'games_count': 0
            }
        
        tournament_info = self.tournament_cache[tournament_id]
        tournament_info['last_update'] = datetime.now()
        tournament_info['files_processed'] += 1
        tournament_info['games_count'] += result.get('games_processed', 0)
        
        return result
    
    def _extract_tournament_id(self, file_path: str) -> str:
        """Extract tournament ID from file path."""
        path_obj = Path(file_path)
        # Use parent directory name as tournament ID
        return path_obj.parent.name
    
    async def _update_tournament_metrics(self, tournament_ids: List[str]):
        """Update metrics for specific tournaments."""
        if not self.metrics_calculator:
            logger.info(f"Test mode: Would update metrics for tournaments: {tournament_ids}")
            return
            
        try:
            # Force refresh metrics for updated tournaments
            await self.metrics_calculator.get_metrics(force_refresh=True)
            logger.info(f"Updated metrics for tournaments: {tournament_ids}")
            
        except Exception as e:
            logger.error(f"Error updating tournament metrics: {e}")
    
    def get_live_tournaments(self) -> List[Dict[str, Any]]:
        """Get currently active tournaments."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        live_tournaments = []
        for tournament_id, info in self.tournament_cache.items():
            if info['last_update'] > cutoff_time:
                # Calculate tournament duration
                duration = info['last_update'] - info['start_time']
                
                live_tournaments.append({
                    'id': tournament_id,
                    'name': self._format_tournament_name(tournament_id),
                    'start_time': info['start_time'].isoformat(),
                    'last_update': info['last_update'].isoformat(),
                    'duration_minutes': int(duration.total_seconds() / 60),
                    'files_processed': info['files_processed'],
                    'games_count': info['games_count'],
                    'status': self._get_tournament_status(info)
                })
        
        # Sort by last update (most recent first)
        live_tournaments.sort(key=lambda x: x['last_update'], reverse=True)
        return live_tournaments
    
    def _format_tournament_name(self, tournament_id: str) -> str:
        """Format tournament ID into readable name."""
        # Extract date and name from ID like "Engine Battle 20250824"
        parts = tournament_id.split()
        if len(parts) >= 3 and parts[-1].isdigit():
            date_str = parts[-1]
            name_parts = parts[:-1]
            if len(date_str) == 8:  # YYYYMMDD format
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
                formatted_date = f"{year}-{month}-{day}"
                return f"{' '.join(name_parts)} ({formatted_date})"
        
        return tournament_id
    
    def _get_tournament_status(self, tournament_info: Dict) -> str:
        """Determine tournament status based on activity."""
        time_since_update = datetime.now() - tournament_info['last_update']
        
        if time_since_update < timedelta(minutes=5):
            return "active"
        elif time_since_update < timedelta(hours=1):
            return "recent"
        else:
            return "completed"
    
    async def get_realtime_stats(self) -> Dict[str, Any]:
        """Get real-time statistics for dashboard."""
        try:
            # Get current metrics (with fallback for test mode)
            if self.metrics_calculator:
                metrics = await self.metrics_calculator.get_metrics()
            else:
                metrics = self._get_test_metrics()
            
            # Get live tournament info
            live_tournaments = self.get_live_tournaments()
            
            # Calculate real-time stats
            stats = {
                'timestamp': datetime.now().isoformat(),
                'live_tournaments': live_tournaments,
                'tournament_count': len(live_tournaments),
                'active_tournaments': len([t for t in live_tournaments if t['status'] == 'active']),
                'total_games_today': self._get_games_today_count(),
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'head_to_head': metrics.get('head_to_head', {}),
                'control_engine_stats': self._get_control_engine_stats(metrics),
                'recent_activity': self._get_recent_activity(),
                'test_mode': not bool(self.metrics_calculator)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting real-time stats: {e}")
            return {'error': str(e)}
    
    def _get_games_today_count(self) -> int:
        """Get count of games played today."""
        today = datetime.now().date()
        count = 0
        
        for tournament_info in self.tournament_cache.values():
            if tournament_info['start_time'].date() == today:
                count += tournament_info['games_count']
        
        return count
    
    def _get_control_engine_stats(self, metrics: Dict) -> Dict[str, Any]:
        """Get C0BR4 control engine statistics."""
        engines = metrics.get('engines', {})
        c0br4_stats = engines.get('c0br4', {})
        
        if not c0br4_stats:
            return {'available': False, 'message': 'No C0BR4 data available'}
        
        # Calculate viability percentage
        total_games = c0br4_stats.get('total_games', 0)
        wins = c0br4_stats.get('wins', 0)
        draws = c0br4_stats.get('draws', 0)
        
        if total_games > 0:
            viability_pct = ((wins + draws * 0.5) / total_games) * 100
        else:
            viability_pct = 0
        
        return {
            'available': True,
            'total_games': total_games,
            'wins': wins,
            'draws': draws,
            'losses': c0br4_stats.get('losses', 0),
            'viability_percentage': round(viability_pct, 1),
            'avg_game_time': c0br4_stats.get('avg_game_time', 0)
        }
    
    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent tournament activity."""
        activities = []
        
        # Sort tournaments by last update
        sorted_tournaments = sorted(
            self.tournament_cache.items(),
            key=lambda x: x[1]['last_update'],
            reverse=True
        )
        
        for tournament_id, info in sorted_tournaments[:5]:  # Last 5 activities
            activities.append({
                'tournament': self._format_tournament_name(tournament_id),
                'timestamp': info['last_update'].isoformat(),
                'games_added': info['games_count'],
                'status': self._get_tournament_status(info)
            })
        
        return activities
    
    def _get_test_metrics(self) -> Dict[str, Any]:
        """Generate test metrics when backend is not available."""
        return {
            'head_to_head': {
                'v7p3r_wins': 15,
                'slowmate_wins': 12,
                'draws': 3,
                'total_games': 30,
                'v7p3r_win_rate': 50.0,
                'slowmate_win_rate': 40.0
            },
            'engines': {
                'c0br4': {
                    'total_games': 25,
                    'wins': 8,
                    'draws': 5,
                    'losses': 12,
                    'avg_game_time': 120.5
                }
            }
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get ETL pipeline status."""
        return {
            'running': self.running,
            'initialized': self.pgn_processor is not None and self.metrics_calculator is not None,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'tournaments_tracked': len(self.tournament_cache),
            'config_loaded': bool(self.config)
        }

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def main():
        etl = RealTimeETL()
        if await etl.initialize():
            logger.info("ETL pipeline ready")
            # Keep running for testing
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("ETL pipeline stopped")
        else:
            logger.error("Failed to initialize ETL pipeline")
    
    asyncio.run(main())
