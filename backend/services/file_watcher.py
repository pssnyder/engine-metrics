import asyncio
import os
import logging
from typing import List, Dict, Any, Set, TYPE_CHECKING
from pathlib import Path
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from watchdog.observers import Observer
else:
    try:
        from watchdog.observers import Observer
    except ImportError:
        Observer = None

from watchdog.events import FileSystemEventHandler

from services.pgn_processor import PGNProcessor

logger = logging.getLogger(__name__)

class PGNFileHandler(FileSystemEventHandler):
    """File system event handler for PGN files."""
    
    def __init__(self, file_watcher):
        self.file_watcher = file_watcher
        self.pending_files: Set[str] = set()
    
    def on_created(self, event):
        if not event.is_directory and self._is_pgn_file(str(event.src_path)):
            logger.info(f"New PGN file detected: {event.src_path}")
            self.pending_files.add(str(event.src_path))
    
    def on_modified(self, event):
        if not event.is_directory and self._is_pgn_file(str(event.src_path)):
            logger.info(f"PGN file modified: {event.src_path}")
            self.pending_files.add(str(event.src_path))
    
    def _is_pgn_file(self, file_path: str) -> bool:
        """Check if file is a PGN file based on extension."""
        return file_path.lower().endswith(('.pgn',))
    
    def get_pending_files(self) -> Set[str]:
        """Get and clear pending files."""
        files = self.pending_files.copy()
        self.pending_files.clear()
        return files

class FileWatcher:
    """Watches directories for new PGN files and coordinates batch processing."""
    
    def __init__(self, config: Dict[str, Any], pgn_processor: PGNProcessor):
        self.config = config
        self.pgn_processor = pgn_processor
        self.observers = []
        self.file_handlers = []
        self.is_running = False
        self.batch_task = None
        
        # Processing settings
        self.batch_interval = config.get('processing', {}).get('batch_interval_minutes', 5)
        self.last_batch_run = datetime.min
        
        # Directory settings
        directories_config = config.get('directories', {})
        self.local_paths = directories_config.get('local_paths', [])
        self.network_paths = directories_config.get('network_paths', [])
        self.file_patterns = directories_config.get('file_patterns', ['*.pgn'])
        
        # Convert relative paths to absolute
        self.local_paths = [self._resolve_path(path) for path in self.local_paths]
        
    def _resolve_path(self, path: str) -> str:
        """Convert relative path to absolute path."""
        if not os.path.isabs(path):
            # Resolve relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            return os.path.abspath(os.path.join(base_dir, path))
        return path
    
    def _validate_directory(self, directory: str) -> bool:
        """Check if directory exists and is accessible."""
        try:
            return os.path.exists(directory) and os.path.isdir(directory)
        except Exception as e:
            logger.error(f"Error accessing directory {directory}: {e}")
            return False
    
    def _scan_directory_for_pgn_files(self, directory: str) -> List[str]:
        """Scan directory for PGN files."""
        pgn_files = []
        
        if not self._validate_directory(directory):
            logger.warning(f"Directory not accessible: {directory}")
            return pgn_files
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(pattern.replace('*', '').lower()) 
                          for pattern in self.file_patterns):
                        file_path = os.path.join(root, file)
                        pgn_files.append(file_path)
        
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
        
        return pgn_files
    
    def get_all_monitored_directories(self) -> List[str]:
        """Get all directories being monitored."""
        all_dirs = []
        
        # Add local paths
        local_paths = self.local_paths or []
        for path in local_paths:
            if self._validate_directory(path):
                all_dirs.append(path)
            else:
                logger.warning(f"Local path not found: {path}")
        
        # Add network paths
        network_paths = self.network_paths or []
        for path in network_paths:
            if self._validate_directory(path):
                all_dirs.append(path)
            else:
                logger.warning(f"Network path not accessible: {path}")
        
        return all_dirs
    
    async def perform_batch_processing(self):
        """Perform batch processing of PGN files."""
        logger.info("Starting batch processing...")
        
        try:
            # Get pending files from file handlers
            pending_files = set()
            for handler in self.file_handlers:
                pending_files.update(handler.get_pending_files())
            
            # Also scan all directories for any missed files
            all_directories = self.get_all_monitored_directories()
            
            for directory in all_directories:
                pgn_files = self._scan_directory_for_pgn_files(directory)
                pending_files.update(pgn_files)
            
            if pending_files:
                logger.info(f"Processing {len(pending_files)} PGN files...")
                
                # Filter to only files that exist and haven't been processed recently
                valid_files = []
                for file_path in pending_files:
                    if os.path.exists(file_path):
                        # Check file modification time to avoid processing incomplete files
                        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if datetime.now() - mtime > timedelta(seconds=30):  # File hasn't been modified in 30 seconds
                            valid_files.append(file_path)
                
                if valid_files:
                    # Process files
                    results = self.pgn_processor.process_multiple_files(valid_files)
                    
                    # Log results
                    total_games = sum(r.get('games_processed', 0) for r in results)
                    successful_files = sum(1 for r in results if r.get('status') == 'success')
                    error_files = sum(1 for r in results if r.get('status') == 'error')
                    
                    logger.info(f"Batch processing complete: {successful_files} files successful, "
                              f"{error_files} files had errors, {total_games} total games processed")
                else:
                    logger.info("No valid files to process in this batch")
            else:
                logger.debug("No pending files for batch processing")
            
            self.last_batch_run = datetime.now()
        
        except Exception as e:
            logger.error(f"Error during batch processing: {e}")
    
    async def batch_processing_loop(self):
        """Main loop for batch processing."""
        while self.is_running:
            try:
                # Check if it's time for batch processing
                if datetime.now() - self.last_batch_run >= timedelta(minutes=self.batch_interval):
                    await self.perform_batch_processing()
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
            
            except Exception as e:
                logger.error(f"Error in batch processing loop: {e}")
                await asyncio.sleep(60)
    
    async def start(self):
        """Start file watching and batch processing."""
        if self.is_running:
            logger.warning("File watcher is already running")
            return
        
        logger.info("Starting file watcher...")
        self.is_running = True
        
        # Set up file system watchers
        monitored_dirs = self.get_all_monitored_directories()
        
        for directory in monitored_dirs:
            try:
                observer = Observer()
                handler = PGNFileHandler(self)
                observer.schedule(handler, directory, recursive=True)
                observer.start()
                
                self.observers.append(observer)
                self.file_handlers.append(handler)
                logger.info(f"Started watching directory: {directory}")
            
            except Exception as e:
                logger.error(f"Failed to watch directory {directory}: {e}")
        
        # Start batch processing loop
        self.batch_task = asyncio.create_task(self.batch_processing_loop())
        
        # Perform initial batch processing
        await self.perform_batch_processing()
        
        logger.info(f"File watcher started successfully, monitoring {len(monitored_dirs)} directories")
    
    async def stop(self):
        """Stop file watching and batch processing."""
        if not self.is_running:
            return
        
        logger.info("Stopping file watcher...")
        self.is_running = False
        
        # Stop file system observers
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        # Cancel batch processing task
        if self.batch_task:
            self.batch_task.cancel()
            try:
                await self.batch_task
            except asyncio.CancelledError:
                pass
        
        self.observers.clear()
        self.file_handlers.clear()
        
        logger.info("File watcher stopped")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current status of file watcher."""
        monitored_dirs = self.get_all_monitored_directories()
        
        return {
            'is_running': self.is_running,
            'monitored_directories': monitored_dirs,
            'last_batch_run': self.last_batch_run.isoformat() if self.last_batch_run != datetime.min else None,
            'batch_interval_minutes': self.batch_interval,
            'observers_count': len(self.observers),
            'next_batch_in_minutes': max(0, self.batch_interval - 
                                       (datetime.now() - self.last_batch_run).total_seconds() / 60)
        }
    
    async def force_batch_processing(self):
        """Force immediate batch processing (for manual triggers)."""
        logger.info("Forcing batch processing...")
        await self.perform_batch_processing()
