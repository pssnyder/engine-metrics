"""
Arena Tournament Monitor Service
Watches the Arena tournaments directory for new files and automatically organizes them.
"""

import os
import shutil
import time
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml
import re

logger = logging.getLogger(__name__)

class ArenaFileHandler(FileSystemEventHandler):
    """Handles file system events from Arena tournaments directory."""
    
    def __init__(self, target_dir: str, config: Dict):
        self.target_dir = Path(target_dir)
        self.config = config
        self.processed_files = set()
        self.tournament_patterns = config.get('tournament_patterns', {})
        
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self._process_file(str(event.src_path))
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            self._process_file(str(event.src_path), is_modification=True)
    
    def _process_file(self, file_path: str, is_modification: bool = False):
        """Process a new or modified tournament file."""
        try:
            file_path_obj = Path(file_path)
            
            # Check if it's a tournament file we care about
            if not self._is_tournament_file(file_path_obj):
                return
                
            # For modifications, always process (tournament might be ongoing)
            if is_modification:
                logger.info(f"Tournament file updated: {file_path_obj.name}")
            
            # Skip if already processed and not a modification
            elif file_path in self.processed_files:
                return
                
            # Wait a moment for file to be fully written
            time.sleep(2)
            
            # Check if this looks like an active tournament
            is_active = self._is_likely_active_tournament(file_path_obj)
            if is_active:
                logger.info(f"Active tournament detected: {file_path_obj.name} - copying for analysis")
            
            # Copy and organize the file (preserving original in Arena)
            destination = self._get_destination_path(file_path_obj)
            if destination:
                self._copy_file(file_path_obj, destination)
                
                # Only mark as processed if it's not an active tournament
                # Active tournaments should be reprocessed on each update
                if not is_active or not is_modification:
                    self.processed_files.add(file_path)
                
                logger.info(f"Processed tournament file: {file_path_obj.name} -> {destination}")
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def _is_likely_active_tournament(self, file_path: Path) -> bool:
        """Check if this appears to be an active tournament."""
        try:
            # Check file modification time - if modified very recently, likely active
            mod_time = file_path.stat().st_mtime
            current_time = time.time()
            time_diff = current_time - mod_time
            
            # If modified within last 10 minutes, consider active
            if time_diff < 600:  # 10 minutes
                return True
            
            # Check file size - if very small, might be just starting
            file_size = file_path.stat().st_size
            if file_size < 1000:  # Less than 1KB, might be starting
                return True
                
            # Check specific file types that indicate ongoing tournaments
            filename_lower = file_path.name.lower()
            if any(indicator in filename_lower for indicator in ['.at', '.log']):
                # Arena tournament files (.at) and logs are often updated during play
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking if tournament is active: {e}")
            return False
    
    def _is_tournament_file(self, file_path: Path) -> bool:
        """Check if the file is a tournament file we should process."""
        file_extensions = self.config.get('file_extensions', ['.pgn', '.txt', '.log', '.html', '.res', '.at'])
        
        # Check extension
        if file_path.suffix.lower() not in file_extensions:
            return False
            
        # Check if filename contains tournament indicators
        filename_lower = file_path.name.lower()
        tournament_indicators = [
            'tournament', 'battle', 'match', 'engine',
            'v7p3r', 'slowmate', 'c0br4'
        ]
        
        return any(indicator in filename_lower for indicator in tournament_indicators)
    
    def _get_destination_path(self, file_path: Path) -> Optional[Path]:
        """Determine the destination path with proper datestamp formatting."""
        try:
            # Try to extract date from filename
            filename = file_path.stem
            date_match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
            
            if date_match:
                year, month, day = date_match.groups()
                tournament_date = f"{year}{month}{day}"
            else:
                # Use today's date if no date found in filename
                today = date.today()
                tournament_date = today.strftime("%Y%m%d")
            
            # Determine tournament type/name
            tournament_name = self._extract_tournament_name(filename, tournament_date)
            
            # Create directory structure
            tournament_dir = self.target_dir / f"{tournament_name} {tournament_date}"
            tournament_dir.mkdir(parents=True, exist_ok=True)
            
            return tournament_dir / file_path.name
            
        except Exception as e:
            logger.error(f"Error determining destination for {file_path}: {e}")
            return None
    
    def _extract_tournament_name(self, filename: str, date_str: str) -> str:
        """Extract tournament name from filename."""
        filename_lower = filename.lower()
        
        # Common tournament name patterns
        if 'engine battle' in filename_lower:
            return "Engine Battle"
        elif 'slowmate' in filename_lower and 'tournament' in filename_lower:
            return "SlowMate Tournament"
        elif 'tournament' in filename_lower:
            return "Tournament"
        elif 'battle' in filename_lower:
            return "Engine Battle"
        elif 'match' in filename_lower:
            return "Engine Match"
        else:
            return "Tournament"
    
    def _copy_file(self, source: Path, destination: Path):
        """Copy file to destination, handling conflicts. Preserves original in Arena directory."""
        try:
            # For active tournaments, always update the copy
            is_active = self._is_likely_active_tournament(source)
            
            if destination.exists() and not is_active:
                # If file exists and tournament is not active, compare sizes
                source_size = source.stat().st_size
                dest_size = destination.stat().st_size
                
                if source_size != dest_size:
                    # Different sizes, append timestamp to avoid overwrite
                    timestamp = datetime.now().strftime("%H%M%S")
                    stem = destination.stem
                    suffix = destination.suffix
                    destination = destination.parent / f"{stem}_{timestamp}{suffix}"
                elif source.stat().st_mtime <= destination.stat().st_mtime:
                    # Destination is newer or same, skip copy
                    logger.debug(f"Skipping copy - destination is up to date: {source.name}")
                    return
            elif destination.exists() and is_active:
                # For active tournaments, overwrite to keep updated
                logger.info(f"Updating active tournament file: {source.name}")
            
            # Copy file, preserving original in Arena directory
            shutil.copy2(str(source), str(destination))
            
            if is_active:
                logger.info(f"Updated active tournament: {source.name} -> {destination}")
            else:
                logger.info(f"Copied: {source.name} -> {destination}")
            
        except Exception as e:
            logger.error(f"Error copying file {source} to {destination}: {e}")

class ArenaMonitor:
    """Main Arena tournament monitor service."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.observer = None
        self.handler = None
        self.running = False
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration."""
        if not config_path:
            config_path = str(Path(__file__).parent.parent / "config" / "settings.yaml")
            
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                return config.get('arena_monitor', {})
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def start(self):
        """Start monitoring the Arena tournaments directory."""
        try:
            arena_dir = self.config.get('arena_tournaments_dir', 
                r"C:\Program Files (x86)\Arena\Tournaments")
            target_dir = self.config.get('target_dir', 
                r"S:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics\game_records")
            
            if not os.path.exists(arena_dir):
                logger.error(f"Arena tournaments directory not found: {arena_dir}")
                return False
                
            # Create target directory if it doesn't exist
            Path(target_dir).mkdir(parents=True, exist_ok=True)
            
            # Set up file handler
            self.handler = ArenaFileHandler(target_dir, self.config)
            
            # Set up observer
            self.observer = Observer()
            self.observer.schedule(self.handler, arena_dir, recursive=True)
            
            # Start monitoring
            self.observer.start()
            self.running = True
            
            logger.info(f"Started monitoring Arena tournaments directory: {arena_dir}")
            logger.info(f"Target directory: {target_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting Arena monitor: {e}")
            return False
    
    def stop(self):
        """Stop monitoring."""
        if self.observer and self.running:
            self.observer.stop()
            self.observer.join()
            self.running = False
            logger.info("Stopped Arena monitor")
    
    def get_status(self) -> Dict:
        """Get monitor status."""
        return {
            'running': self.running,
            'files_processed': len(self.handler.processed_files) if self.handler else 0,
            'arena_dir': self.config.get('arena_tournaments_dir'),
            'target_dir': self.config.get('target_dir')
        }

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start monitor
    monitor = ArenaMonitor()
    if monitor.start():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            monitor.stop()
    else:
        logger.error("Failed to start Arena monitor")
