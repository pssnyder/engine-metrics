#!/usr/bin/env python3
"""
Ingest Layer - Chess Engine Metrics Pipeline
Monitors Cloud Storage bucket for new files and ingests them into BigQuery data lake
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from google.cloud import storage, bigquery, pubsub_v1
from google.cloud.exceptions import NotFound
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingest_layer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('IngestLayer')

class SchemaManager:
    """Manages BigQuery table schemas for different data types"""
    
    @staticmethod
    def get_pgn_schema():
        """Schema for PGN game files"""
        return [
            bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("event", "STRING"),
            bigquery.SchemaField("site", "STRING"),
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("round", "STRING"),
            bigquery.SchemaField("white", "STRING"),
            bigquery.SchemaField("black", "STRING"),
            bigquery.SchemaField("result", "STRING"),
            bigquery.SchemaField("white_elo", "INTEGER"),
            bigquery.SchemaField("black_elo", "INTEGER"),
            bigquery.SchemaField("time_control", "STRING"),
            bigquery.SchemaField("opening", "STRING"),
            bigquery.SchemaField("moves", "STRING"),
            bigquery.SchemaField("move_count", "INTEGER"),
            bigquery.SchemaField("game_duration", "INTEGER"),
            bigquery.SchemaField("termination", "STRING"),
            bigquery.SchemaField("source_file", "STRING"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP"),
            bigquery.SchemaField("file_modified_at", "TIMESTAMP"),
        ]
    
    @staticmethod
    def get_analysis_schema():
        """Schema for analysis result files"""
        return [
            bigquery.SchemaField("analysis_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("engine_version", "STRING"),
            bigquery.SchemaField("analysis_type", "STRING"),
            bigquery.SchemaField("analysis_date", "TIMESTAMP"),
            bigquery.SchemaField("position_fen", "STRING"),
            bigquery.SchemaField("depth", "INTEGER"),
            bigquery.SchemaField("evaluation", "FLOAT"),
            bigquery.SchemaField("best_move", "STRING"),
            bigquery.SchemaField("pv_line", "STRING"),
            bigquery.SchemaField("nodes_searched", "INTEGER"),
            bigquery.SchemaField("time_ms", "INTEGER"),
            bigquery.SchemaField("nps", "INTEGER"),
            bigquery.SchemaField("analysis_data", "JSON"),
            bigquery.SchemaField("source_file", "STRING"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP"),
        ]
    
    @staticmethod
    def get_documentation_schema():
        """Schema for documentation files"""
        return [
            bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("content", "STRING"),
            bigquery.SchemaField("doc_type", "STRING"),
            bigquery.SchemaField("engine_version", "STRING"),
            bigquery.SchemaField("created_date", "DATE"),
            bigquery.SchemaField("tags", "STRING", mode="REPEATED"),
            bigquery.SchemaField("source_file", "STRING"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP"),
        ]

class DataProcessor:
    """Processes different file types into structured data"""
    
    @staticmethod
    def process_pgn_file(file_content: str, source_file: str) -> List[Dict]:
        """Process PGN file into structured game records using python-chess for robust parsing"""
        try:
            import chess.pgn
            from io import StringIO
        except ImportError:
            logger.error("python-chess library not available for PGN parsing")
            return []
        
        games = []
        pgn_io = StringIO(file_content)
        
        game_index = 0
        while True:
            try:
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    break
                    
                # Extract headers
                headers = dict(game.headers)
                
                # Extract moves in SAN (Standard Algebraic Notation)
                moves = []
                board = game.board()
                for move in game.mainline_moves():
                    moves.append(board.san(move))
                    board.push(move)
                
                # Parse date if available
                date_str = headers.get('Date', '????.??.??')
                parsed_date = None
                if date_str and date_str != '????.??.??':
                    try:
                        # Common PGN date formats
                        for fmt in ['%Y.%m.%d', '%Y-%m-%d', '%Y/%m/%d']:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt).date().isoformat()
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass
                
                # Parse ELO ratings
                white_elo = None
                black_elo = None
                try:
                    if 'WhiteElo' in headers and headers['WhiteElo'].isdigit():
                        white_elo = int(headers['WhiteElo'])
                    if 'BlackElo' in headers and headers['BlackElo'].isdigit():
                        black_elo = int(headers['BlackElo'])
                except (ValueError, KeyError):
                    pass
                
                # Create structured record
                game_record = {
                    'game_id': f"{source_file}_{game_index}",
                    'event': headers.get('Event', 'Unknown Event'),
                    'site': headers.get('Site', 'Unknown Site'),
                    'date': parsed_date,
                    'round': headers.get('Round', '1'),
                    'white': headers.get('White', 'Unknown White'),
                    'black': headers.get('Black', 'Unknown Black'),
                    'result': headers.get('Result', '*'),
                    'white_elo': white_elo,
                    'black_elo': black_elo,
                    'time_control': headers.get('TimeControl'),
                    'opening': headers.get('Opening'),
                    'moves': ' '.join(moves),
                    'move_count': len(moves),
                    'game_duration': None,  # Could calculate from timestamps if available
                    'termination': headers.get('Termination'),
                    'source_file': source_file,
                    'ingested_at': datetime.utcnow(),
                    'file_modified_at': datetime.utcnow()
                }
                
                games.append(game_record)
                game_index += 1
                
            except Exception as e:
                logger.warning(f"Error parsing game {game_index} in {source_file}: {e}")
                break
                
        return games
    
    @staticmethod
    def process_analysis_file(file_content: str, source_file: str) -> List[Dict]:
        """Process analysis JSON file into structured records"""
        try:
            data = json.loads(file_content)
            
            # Handle different analysis file formats
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict) and 'analysis_results' in data:
                records = data['analysis_results']
            else:
                records = [data]
            
            processed = []
            for i, record in enumerate(records):
                processed_record = {
                    'analysis_id': f"{source_file}_{i}",
                    'engine_version': record.get('engine_version', ''),
                    'analysis_type': record.get('type', 'unknown'),
                    'analysis_date': record.get('timestamp', datetime.utcnow().isoformat()),
                    'position_fen': record.get('position', ''),
                    'depth': record.get('depth', 0),
                    'evaluation': record.get('evaluation', 0.0),
                    'best_move': record.get('best_move', ''),
                    'pv_line': record.get('pv', ''),
                    'nodes_searched': record.get('nodes', 0),
                    'time_ms': record.get('time', 0),
                    'nps': record.get('nps', 0),
                    'analysis_data': json.dumps(record),
                    'source_file': source_file,
                    'ingested_at': datetime.utcnow().isoformat()
                }
                processed.append(processed_record)
            
            return processed
        
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON file: {source_file}")
            return []
    
    @staticmethod
    def process_documentation_file(file_content: str, source_file: str) -> List[Dict]:
        """Process documentation markdown file"""
        # Extract title from first header or filename
        title = source_file
        lines = file_content.split('\n')
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        # Extract engine version from filename or content
        engine_version = 'unknown'
        if 'v7p3r' in source_file.lower():
            import re
            version_match = re.search(r'v(\d+)[\._](\d+)', source_file)
            if version_match:
                engine_version = f"v{version_match.group(1)}.{version_match.group(2)}"
        
        return [{
            'doc_id': source_file,
            'title': title,
            'content': file_content,
            'doc_type': 'markdown',
            'engine_version': engine_version,
            'created_date': datetime.utcnow().date().isoformat(),
            'tags': [],  # Could extract from content
            'source_file': source_file,
            'ingested_at': datetime.utcnow().isoformat()
        }]

class BigQueryManager:
    """Manages BigQuery operations"""
    
    def __init__(self, project_id: str, dataset_name: str = "chess_engine_data_lake"):
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id
        self.dataset_name = dataset_name
        self.dataset_ref = self.client.dataset(dataset_name)
        
        # Ensure dataset exists
        self._create_dataset_if_not_exists()
        
        # Table configurations
        self.tables = {
            'games': ('pgn_games', SchemaManager.get_pgn_schema()),
            'analysis': ('analysis_results', SchemaManager.get_analysis_schema()),
            'documentation': ('documentation', SchemaManager.get_documentation_schema())
        }
        
        # Ensure all tables exist
        self._create_tables_if_not_exist()
    
    def _create_dataset_if_not_exists(self):
        """Create BigQuery dataset if it doesn't exist"""
        try:
            self.client.get_dataset(self.dataset_ref)
            logger.info(f"✅ Dataset {self.dataset_name} exists")
        except NotFound:
            dataset = bigquery.Dataset(self.dataset_ref)
            dataset.location = "US"
            dataset.description = "Chess Engine Metrics Data Lake"
            
            dataset = self.client.create_dataset(dataset)
            logger.info(f"✅ Created dataset {self.dataset_name}")
    
    def _create_tables_if_not_exist(self):
        """Create all required tables if they don't exist"""
        for data_type, (table_name, schema) in self.tables.items():
            table_ref = self.dataset_ref.table(table_name)
            try:
                self.client.get_table(table_ref)
                logger.info(f"✅ Table {table_name} exists")
            except NotFound:
                table = bigquery.Table(table_ref, schema=schema)
                table = self.client.create_table(table)
                logger.info(f"✅ Created table {table_name}")
    
    def insert_records(self, data_type: str, records: List[Dict]) -> bool:
        """Insert records into the appropriate table"""
        if not records:
            return True
        
        table_name, _ = self.tables[data_type]
        table_ref = self.dataset_ref.table(table_name)
        
        try:
            errors = self.client.insert_rows_json(
                self.client.get_table(table_ref), 
                records
            )
            
            if errors:
                logger.error(f"❌ Errors inserting into {table_name}: {errors}")
                return False
            
            logger.info(f"✅ Inserted {len(records)} records into {table_name}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to insert records into {table_name}: {e}")
            return False

class CloudStorageMonitor:
    """Monitors Cloud Storage bucket for new files"""
    
    def __init__(self, bucket_name: str, bq_manager: BigQueryManager):
        self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        self.bucket = self.storage_client.bucket(bucket_name)
        self.bq_manager = bq_manager
        self.processor = DataProcessor()
        
        # Track processed files
        self.processed_files = self._load_processed_files()
        
        logger.info(f"☁️  Monitoring bucket: gs://{bucket_name}")
    
    def _load_processed_files(self) -> set:
        """Load list of already processed files"""
        processed_file = 'processed_files.json'
        if os.path.exists(processed_file):
            try:
                with open(processed_file, 'r') as f:
                    return set(json.load(f))
            except:
                pass
        return set()
    
    def _save_processed_files(self):
        """Save list of processed files"""
        with open('processed_files.json', 'w') as f:
            json.dump(list(self.processed_files), f)
    
    def scan_for_new_files(self) -> List[storage.Blob]:
        """Scan bucket for new files to process"""
        new_files = []
        
        for blob in self.bucket.list_blobs():
            if blob.name not in self.processed_files:
                new_files.append(blob)
        
        return new_files
    
    def process_file(self, blob: storage.Blob) -> bool:
        """Process a single file from storage"""
        try:
            logger.info(f"🔄 Processing: {blob.name}")
            
            # Download file content
            content = blob.download_as_text()
            
            # Determine file type and process accordingly
            file_ext = Path(blob.name).suffix.lower()
            
            if file_ext == '.pgn':
                records = self.processor.process_pgn_file(content, blob.name)
                success = self.bq_manager.insert_records('games', records)
            
            elif file_ext == '.json':
                records = self.processor.process_analysis_file(content, blob.name)
                success = self.bq_manager.insert_records('analysis', records)
            
            elif file_ext in ['.md', '.txt']:
                records = self.processor.process_documentation_file(content, blob.name)
                success = self.bq_manager.insert_records('documentation', records)
            
            else:
                logger.warning(f"⚠️  Unsupported file type: {blob.name}")
                success = True  # Skip unsupported files
            
            if success:
                self.processed_files.add(blob.name)
                self._save_processed_files()
                logger.info(f"✅ Successfully processed: {blob.name}")
            
            return success
        
        except Exception as e:
            logger.error(f"❌ Error processing {blob.name}: {e}")
            return False
    
    def run_batch_ingestion(self) -> Dict[str, int]:
        """Run one-time batch ingestion of all new files"""
        new_files = self.scan_for_new_files()
        logger.info(f"📥 Found {len(new_files)} new files to process")
        
        stats = {'processed': 0, 'failed': 0, 'skipped': 0}
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_blob = {executor.submit(self.process_file, blob): blob 
                             for blob in new_files}
            
            for future in future_to_blob:
                blob = future_to_blob[future]
                try:
                    if future.result():
                        stats['processed'] += 1
                    else:
                        stats['failed'] += 1
                except Exception as e:
                    logger.error(f"❌ Exception processing {blob.name}: {e}")
                    stats['failed'] += 1
        
        return stats
    
    def start_continuous_monitoring(self, polling_interval: int = 60):
        """Start continuous monitoring for new files"""
        logger.info(f"🔄 Starting continuous monitoring (polling every {polling_interval}s)")
        
        while True:
            try:
                new_files = self.scan_for_new_files()
                
                if new_files:
                    logger.info(f"📥 Found {len(new_files)} new files")
                    for blob in new_files:
                        self.process_file(blob)
                
                time.sleep(polling_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Stopping continuous monitoring")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(polling_interval)

class IngestLayer:
    """Main Ingest Layer orchestrator"""
    
    def __init__(self, config_path: str = "ingest_layer_config.json"):
        self.config = self._load_config(config_path)['ingest_layer_config']
        
        # Initialize components
        self.bq_manager = BigQueryManager(
            project_id=self.config['bigquery']['project_id'],
            dataset_name=self.config['bigquery']['dataset_name']
        )
        
        self.storage_monitor = CloudStorageMonitor(
            bucket_name=self.config['storage']['bucket_name'],
            bq_manager=self.bq_manager
        )
        
        logger.info("🚀 Ingest Layer initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"❌ Config file not found: {config_path}")
            raise
    
    def run_initial_ingestion(self):
        """Run one-time ingestion of all existing files"""
        logger.info("📊 Starting initial data ingestion...")
        stats = self.storage_monitor.run_batch_ingestion()
        
        logger.info(f"📊 Initial ingestion complete:")
        logger.info(f"   • Processed: {stats['processed']} files")
        logger.info(f"   • Failed: {stats['failed']} files")
        logger.info(f"   • Skipped: {stats['skipped']} files")
        
        return stats
    
    def start_monitoring(self):
        """Start continuous monitoring for new files"""
        polling_interval = self.config.get('monitoring', {}).get('polling_interval', 60)
        self.storage_monitor.start_continuous_monitoring(polling_interval)
    
    def get_status(self) -> Dict:
        """Get current status of the ingest layer"""
        return {
            'bucket': self.storage_monitor.bucket_name,
            'dataset': self.bq_manager.dataset_name,
            'processed_files_count': len(self.storage_monitor.processed_files),
            'last_check': datetime.utcnow().isoformat()
        }

def main():
    """Main function"""
    ingest_layer = IngestLayer()
    
    # Run initial ingestion
    ingest_layer.run_initial_ingestion()
    
    # Start continuous monitoring
    ingest_layer.start_monitoring()

if __name__ == "__main__":
    main()