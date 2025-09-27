import os
import time
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from google.cloud import storage
import logging

# Import path mappings
try:
    from path_mappings import get_bucket_path, get_local_path
except ImportError:
    # Fallback if path_mappings not available
    def get_bucket_path(local_path):
        return local_path
    def get_local_path(bucket_path):
        return bucket_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('move_layer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MoveLayer')

class CloudStorageUploader:
    """Handles file uploads to Google Cloud Storage"""
    
    def __init__(self, bucket_name, credentials_path=None):
        self.bucket_name = bucket_name
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            logger.info(f"✅ Connected to GCS bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to GCS: {e}")
            self.client = None
            self.bucket = None

    def upload_file(self, local_path, cloud_path):
        """Upload a file to cloud storage"""
        if not self.bucket:
            logger.error("❌ No valid GCS connection")
            return False
            
        try:
            blob = self.bucket.blob(cloud_path)
            
            # Upload with metadata
            blob.upload_from_filename(
                local_path,
                content_type=self._get_content_type(local_path)
            )
            
            # Set metadata
            blob.metadata = {
                'source': 'chess-engine-raw-data',
                'upload_time': datetime.utcnow().isoformat(),
                'local_path': str(local_path),
                'file_size': str(os.path.getsize(local_path))
            }
            blob.patch()
            
            logger.info(f"✅ Uploaded: {local_path} → gs://{self.bucket_name}/{cloud_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Upload failed for {local_path}: {e}")
            return False

    def _get_content_type(self, file_path):
        """Determine content type based on file extension"""
        ext = Path(file_path).suffix.lower()
        content_types = {
            '.pgn': 'application/x-chess-pgn',
            '.json': 'application/json',
            '.csv': 'text/csv',
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.log': 'text/plain'
        }
        return content_types.get(ext, 'application/octet-stream')

class FileTracker:
    """Tracks file states and detects changes"""
    
    def __init__(self, state_file='file_tracker_state.json'):
        self.state_file = state_file
        self.file_states = self._load_state()
    
    def _load_state(self):
        """Load previous file states from disk"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️  Could not load state file: {e}")
        return {}
    
    def _save_state(self):
        """Save current file states to disk"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.file_states, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Could not save state file: {e}")
    
    def _get_file_hash(self, file_path):
        """Calculate file hash for change detection"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"❌ Could not hash file {file_path}: {e}")
            return None
    
    def is_file_changed(self, file_path):
        """Check if file has changed since last scan"""
        try:
            stat = os.stat(file_path)
            current_state = {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'hash': self._get_file_hash(file_path)
            }
            
            file_key = str(file_path)
            previous_state = self.file_states.get(file_key)
            
            if not previous_state:
                # New file
                self.file_states[file_key] = current_state
                self._save_state()
                return True
            
            # Check if changed
            if (current_state['size'] != previous_state['size'] or
                current_state['mtime'] != previous_state['mtime'] or
                current_state['hash'] != previous_state['hash']):
                
                self.file_states[file_key] = current_state
                self._save_state()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking file state for {file_path}: {e}")
            return False

class RawDataFileHandler(FileSystemEventHandler):
    """Handles file system events in the raw_data directory"""
    
    def __init__(self, uploader, tracker, base_path):
        self.uploader = uploader
        self.tracker = tracker
        self.base_path = Path(base_path)
        self.pending_uploads = set()
        
    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_upload(event.src_path)
    
    def on_created(self, event):
        if not event.is_directory:
            self._schedule_upload(event.src_path)
    
    def on_moved(self, event):
        if not event.is_directory:
            self._schedule_upload(event.dest_path)
    
    def _schedule_upload(self, file_path):
        """Schedule a file for upload after a brief delay to ensure file is complete"""
        if file_path in self.pending_uploads:
            return
            
        self.pending_uploads.add(file_path)
        
        # Add a small delay to ensure file write is complete
        def delayed_upload():
            time.sleep(2)  # Wait 2 seconds
            if file_path in self.pending_uploads:
                self._process_file(file_path)
                self.pending_uploads.discard(file_path)
        
        import threading
        thread = threading.Thread(target=delayed_upload)
        thread.daemon = True
        thread.start()
    
    def _process_file(self, file_path):
        """Process a single file for upload"""
        try:
            file_path = Path(file_path)
            
            # Skip temporary files, hidden files, and directories
            if (file_path.name.startswith('.') or 
                file_path.name.endswith('.tmp') or
                not file_path.is_file()):
                return
            
            # Check if file has actually changed
            if not self.tracker.is_file_changed(file_path):
                logger.debug(f"📋 No change detected: {file_path}")
                return
            
            # Calculate cloud path using path mappings
            relative_path = file_path.relative_to(self.base_path)
            cloud_path = get_bucket_path(relative_path.as_posix())
            
            logger.info(f"🔄 Processing: {file_path}")
            
            # Upload to cloud storage
            if self.uploader.upload_file(file_path, cloud_path):
                logger.info(f"✅ Successfully processed: {file_path}")
            else:
                logger.error(f"❌ Failed to process: {file_path}")
                
        except Exception as e:
            logger.error(f"❌ Error processing file {file_path}: {e}")

class MoveLayer:
    """Main class for the Move Layer - monitors and transfers files"""
    
    def __init__(self, raw_data_path, bucket_name, credentials_path=None):
        self.raw_data_path = Path(raw_data_path)
        self.uploader = CloudStorageUploader(bucket_name, credentials_path)
        self.tracker = FileTracker()
        self.observer = Observer()
        self.is_running = False
        
        logger.info(f"🚀 MoveLayer initialized")
        logger.info(f"📁 Monitoring: {self.raw_data_path}")
        logger.info(f"☁️  Target bucket: {bucket_name}")
    
    def perform_initial_sync(self):
        """Perform initial sync of all files in raw_data directory"""
        logger.info("🔄 Starting initial sync...")
        
        total_files = 0
        uploaded_files = 0
        
        for root, dirs, files in os.walk(self.raw_data_path):
            for file in files:
                file_path = Path(root) / file
                
                # Skip hidden files and temp files
                if file.startswith('.') or file.endswith('.tmp'):
                    continue
                
                total_files += 1
                
                if self.tracker.is_file_changed(file_path):
                    relative_path = file_path.relative_to(self.raw_data_path)
                    cloud_path = get_bucket_path(relative_path.as_posix())
                    
                    if self.uploader.upload_file(file_path, cloud_path):
                        uploaded_files += 1
                        logger.info(f"✅ Synced: {relative_path}")
                    else:
                        logger.error(f"❌ Failed to sync: {relative_path}")
        
        logger.info(f"📊 Initial sync complete: {uploaded_files}/{total_files} files uploaded")
    
    def start_monitoring(self):
        """Start real-time file monitoring"""
        if self.is_running:
            logger.warning("⚠️  Already monitoring")
            return
        
        handler = RawDataFileHandler(self.uploader, self.tracker, self.raw_data_path)
        self.observer.schedule(handler, str(self.raw_data_path), recursive=True)
        
        self.observer.start()
        self.is_running = True
        
        logger.info("👀 Real-time monitoring started")
        logger.info("📡 Watching for file changes...")
    
    def stop_monitoring(self):
        """Stop file monitoring"""
        if not self.is_running:
            return
        
        self.observer.stop()
        self.observer.join()
        self.is_running = False
        
        logger.info("⏹️  Monitoring stopped")
    
    def get_status(self):
        """Get current status of the move layer"""
        return {
            'is_monitoring': self.is_running,
            'raw_data_path': str(self.raw_data_path),
            'bucket_name': self.uploader.bucket_name if self.uploader.bucket else None,
            'bucket_connected': self.uploader.bucket is not None,
            'files_tracked': len(self.tracker.file_states),
            'last_updated': datetime.utcnow().isoformat()
        }

if __name__ == '__main__':
    # Configuration
    RAW_DATA_PATH = r"S:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics\raw_data"
    BUCKET_NAME = "chess-engine-raw-data"
    CREDENTIALS_PATH = None  # Use default credentials or set path
    
    # Initialize Move Layer
    move_layer = MoveLayer(RAW_DATA_PATH, BUCKET_NAME, CREDENTIALS_PATH)
    
    # Perform initial sync
    move_layer.perform_initial_sync()
    
    # Start monitoring
    move_layer.start_monitoring()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
        move_layer.stop_monitoring()
        logger.info("✅ Move Layer shutdown complete")