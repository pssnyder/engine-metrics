"""
Chess Engine Metrics AI - Knowledge Base Management
Handles data processing, storage, and retrieval for AI analysis
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from google.cloud import storage
import chess.pgn
import io

# Set up authentication using Firebase CLI credentials
os.environ.setdefault('GOOGLE_CLOUD_PROJECT', 'chess-engine-metrics-agent')

class ChessEngineKnowledgeBase:
    def __init__(self, project_id: Optional[str] = None):
        """Initialize the knowledge base with Firebase connections"""
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT', 'chess-engine-metrics-agent')
        
        # Initialize Firebase clients with Application Default Credentials
        try:
            # Use Application Default Credentials (Firebase CLI authentication)
            self.db = firestore.Client(project=self.project_id)
            self.storage_client = storage.Client(project=self.project_id)
            self.bucket = self.storage_client.bucket(f"{self.project_id}.firebasestorage.app")
            
            # Test the connection
            self._test_connection()
            print(f"[SUCCESS] Connected to Firebase project: {self.project_id}")
            
        except Exception as e:
            print(f"[WARNING] Firebase connection issue: {e}")
            print("[INFO] Ensure you're authenticated with: firebase login")
            print("Using fallback mode - some features may be limited")
            self.db = None
            self.storage_client = None
            self.bucket = None
    
    def _test_connection(self):
        """Test Firebase connections"""
        if self.db:
            # Test Firestore connection
            test_ref = self.db.collection('_test').document('connection')
            test_ref.set({'timestamp': firestore.SERVER_TIMESTAMP}, merge=True)
        
        if self.bucket:
            # Test Storage connection by checking if bucket exists
            self.bucket.exists()
        
    def ingest_pgn_data(self, pgn_content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process PGN content and extract game data"""
        try:
            if not self.db:
                return {
                    'success': False,
                    'error': 'Database connection not available'
                }
            
            games = []
            pgn_io = io.StringIO(pgn_content)
            
            while True:
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    break
                    
                game_data = self._extract_game_data(game)
                if game_data:
                    games.append(game_data)
            
            # Analyze engine performance
            engine_stats = self._analyze_engine_performance(games)
            
            # Store processed data
            processed_data = {
                'source_file': metadata.get('fileName', 'unknown'),
                'total_games': len(games),
                'games': games[:100],  # Store first 100 games
                'engine_performance': engine_stats,
                'processed_at': datetime.utcnow().isoformat(),
                'data_type': 'pgn_analysis'
            }
            
            # Save to Firestore
            doc_ref = self.db.collection('knowledge_base').add(processed_data)
            
            return {
                'success': True,
                'games_processed': len(games),
                'engine_stats': engine_stats,
                'document_id': doc_ref[1].id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def ingest_json_data(self, json_content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process JSON analysis data"""
        try:
            if not self.db:
                return {
                    'success': False,
                    'error': 'Database connection not available'
                }
            
            data = json.loads(json_content)
            
            # Extract performance metrics
            metrics = self._extract_json_metrics(data)
            
            processed_data = {
                'source_file': metadata.get('fileName', 'unknown'),
                'raw_data': data,
                'extracted_metrics': metrics,
                'processed_at': datetime.utcnow().isoformat(),
                'data_type': 'json_analysis'
            }
            
            # Save to Firestore
            doc_ref = self.db.collection('knowledge_base').add(processed_data)
            
            return {
                'success': True,
                'metrics_extracted': len(metrics),
                'document_id': doc_ref[1].id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def ingest_markdown_data(self, md_content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process Markdown documentation"""
        try:
            if not self.db:
                return {
                    'success': False,
                    'error': 'Database connection not available'
                }
            
            # Extract structured information
            analysis = self._analyze_markdown_content(md_content)
            
            processed_data = {
                'source_file': metadata.get('fileName', 'unknown'),
                'content': md_content,
                'analysis': analysis,
                'processed_at': datetime.utcnow().isoformat(),
                'data_type': 'markdown_analysis'
            }
            
            # Save to Firestore
            doc_ref = self.db.collection('knowledge_base').add(processed_data)
            
            return {
                'success': True,
                'sections_found': len(analysis.get('sections', [])),
                'document_id': doc_ref[1].id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def query_knowledge_base(self, query_type: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query the knowledge base for relevant data"""
        try:
            if not self.db:
                return []
            
            # Build query
            collection_ref = self.db.collection('knowledge_base')
            
            if filters:
                if 'data_type' in filters:
                    collection_ref = collection_ref.where('data_type', '==', filters['data_type'])
                if 'engine' in filters:
                    # This would need more sophisticated querying in production
                    pass
            
            # Execute query
            docs = collection_ref.order_by('processed_at', direction=firestore.Query.DESCENDING).limit(50).stream()
            
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
            
            return results
            
        except Exception as e:
            print(f"Query error: {e}")
            return []
    
    def get_engine_performance_summary(self, engine_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary for specific engine or all engines"""
        try:
            if not self.db:
                return {
                    'engines': {},
                    'total_games_analyzed': 0,
                    'error': 'Database connection not available'
                }
            
            # Query PGN analysis data
            pgn_data = self.query_knowledge_base('performance', {'data_type': 'pgn_analysis'})
            
            # Aggregate performance data
            all_stats = {}
            total_games = 0
            
            for doc in pgn_data:
                if 'engine_performance' in doc:
                    for engine, stats in doc['engine_performance'].items():
                        if engine_name and engine.lower() != engine_name.lower():
                            continue
                            
                        if engine not in all_stats:
                            all_stats[engine] = {'wins': 0, 'draws': 0, 'losses': 0, 'total': 0}
                        
                        all_stats[engine]['wins'] += stats.get('wins', 0)
                        all_stats[engine]['draws'] += stats.get('draws', 0)
                        all_stats[engine]['losses'] += stats.get('losses', 0)
                        all_stats[engine]['total'] += stats.get('total', 0)
                
                total_games += doc.get('total_games', 0)
            
            # Calculate win rates
            for engine, stats in all_stats.items():
                if stats['total'] > 0:
                    stats['win_rate'] = round((stats['wins'] / stats['total']) * 100, 2)
                    stats['draw_rate'] = round((stats['draws'] / stats['total']) * 100, 2)
                    stats['loss_rate'] = round((stats['losses'] / stats['total']) * 100, 2)
                else:
                    stats['win_rate'] = stats['draw_rate'] = stats['loss_rate'] = 0
            
            return {
                'engines': all_stats,
                'total_games_analyzed': total_games,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'engines': {},
                'total_games_analyzed': 0,
                'error': str(e)
            }
    
    def _extract_game_data(self, game) -> Optional[Dict[str, Any]]:
        """Extract structured data from a chess game"""
        try:
            headers = game.headers
            
            return {
                'white': headers.get('White', 'Unknown'),
                'black': headers.get('Black', 'Unknown'),
                'result': headers.get('Result', '*'),
                'date': headers.get('Date', '????.??.??'),
                'event': headers.get('Event', 'Unknown'),
                'round': headers.get('Round', '?'),
                'time_control': headers.get('TimeControl', 'Unknown'),
                'white_elo': self._parse_elo(headers.get('WhiteElo', '?')),
                'black_elo': self._parse_elo(headers.get('BlackElo', '?')),
                'moves': len(list(game.mainline_moves())),
                'termination': headers.get('Termination', 'Unknown')
            }
            
        except Exception as e:
            print(f"Error extracting game data: {e}")
            return None
    
    def _parse_elo(self, elo_str: str) -> Optional[int]:
        """Parse ELO rating from string"""
        try:
            return int(elo_str) if elo_str != '?' else None
        except (ValueError, TypeError):
            return None
    
    def _analyze_engine_performance(self, games: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        """Analyze performance statistics for engines"""
        engine_stats = {}
        
        for game in games:
            white_engine = game['white']
            black_engine = game['black']
            result = game['result']
            
            # Initialize engine stats if not exists
            for engine in [white_engine, black_engine]:
                if engine not in engine_stats:
                    engine_stats[engine] = {'wins': 0, 'draws': 0, 'losses': 0, 'total': 0}
                engine_stats[engine]['total'] += 1
            
            # Update win/loss/draw counts
            if result == '1-0':  # White wins
                engine_stats[white_engine]['wins'] += 1
                engine_stats[black_engine]['losses'] += 1
            elif result == '0-1':  # Black wins
                engine_stats[black_engine]['wins'] += 1
                engine_stats[white_engine]['losses'] += 1
            elif result == '1/2-1/2':  # Draw
                engine_stats[white_engine]['draws'] += 1
                engine_stats[black_engine]['draws'] += 1
        
        return engine_stats
    
    def _extract_json_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract performance metrics from JSON data"""
        metrics = {}
        
        # Common metric fields
        metric_fields = [
            'elo', 'rating', 'wins', 'losses', 'draws', 'total_games',
            'win_rate', 'loss_rate', 'draw_rate', 'tactical_accuracy',
            'positional_score', 'endgame_score', 'time_management',
            'opening_book_score'
        ]
        
        for field in metric_fields:
            if field in data:
                metrics[field] = data[field]
        
        # Look for nested metrics
        if 'performance' in data:
            metrics.update(data['performance'])
        
        if 'statistics' in data:
            metrics.update(data['statistics'])
        
        return metrics
    
    def _analyze_markdown_content(self, content: str) -> Dict[str, Any]:
        """Analyze markdown content for structured information"""
        lines = content.split('\n')
        sections = []
        current_section = None
        
        for i, line in enumerate(lines):
            # Detect headers
            if line.startswith('#'):
                if current_section:
                    sections.append(current_section)
                
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                current_section = {
                    'level': level,
                    'title': title,
                    'line_number': i + 1,
                    'content': []
                }
            elif current_section:
                current_section['content'].append(line)
        
        if current_section:
            sections.append(current_section)
        
        # Extract key topics
        key_topics = self._extract_key_topics(content)
        
        return {
            'sections': sections,
            'word_count': len(content.split()),
            'key_topics': key_topics,
            'performance_mentions': content.lower().count('performance'),
            'elo_mentions': content.lower().count('elo'),
            'improvement_mentions': content.lower().count('improve')
        }
    
    def _extract_key_topics(self, content: str) -> List[Dict[str, Any]]:
        """Extract key topics and their frequency"""
        content_lower = content.lower()
        
        keywords = {
            'performance': ['performance', 'perform'],
            'tactical': ['tactical', 'tactics', 'tactic'],
            'positional': ['positional', 'position'],
            'endgame': ['endgame', 'ending'],
            'opening': ['opening', 'book'],
            'time_control': ['blitz', 'rapid', 'classical', 'time control'],
            'engine': ['engine', 'chess engine'],
            'elo': ['elo', 'rating'],
            'improvement': ['improve', 'improvement', 'enhance', 'optimization']
        }
        
        topics = []
        for topic, terms in keywords.items():
            count = sum(content_lower.count(term) for term in terms)
            if count > 0:
                topics.append({'topic': topic, 'frequency': count})
        
        return sorted(topics, key=lambda x: x['frequency'], reverse=True)
    
    def load_data_from_storage(self, file_path: str) -> Optional[str]:
        """Load data directly from Firebase Storage bucket"""
        try:
            if not self.bucket:
                return None
            
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                print(f"File not found in storage: {file_path}")
                return None
            
            content = blob.download_as_text()
            print(f"[SUCCESS] Loaded {len(content)} characters from {file_path}")
            return content
            
        except Exception as e:
            print(f"[ERROR] Error loading from storage: {e}")
            return None
    
    def list_storage_files(self, prefix: str = "") -> List[str]:
        """List files in Firebase Storage bucket"""
        try:
            if not self.bucket:
                return []
            
            blobs = self.bucket.list_blobs(prefix=prefix)
            files = [blob.name for blob in blobs]
            print(f"📁 Found {len(files)} files with prefix '{prefix}'")
            return files
            
        except Exception as e:
            print(f"[ERROR] Error listing storage files: {e}")
            return []
    
    def auto_ingest_from_storage(self, prefix: str = "") -> Dict[str, Any]:
        """Automatically ingest all supported files from storage"""
        try:
            files = self.list_storage_files(prefix)
            
            results = {
                'processed': 0,
                'errors': 0,
                'skipped': 0,
                'details': []
            }
            
            for file_path in files:
                # Skip directories and unsupported files
                if file_path.endswith('/'):
                    continue
                
                file_ext = file_path.lower().split('.')[-1]
                
                if file_ext not in ['pgn', 'json', 'md']:
                    results['skipped'] += 1
                    continue
                
                content = self.load_data_from_storage(file_path)
                if not content:
                    results['errors'] += 1
                    results['details'].append(f"Failed to load: {file_path}")
                    continue
                
                # Process based on file type
                metadata = {'fileName': file_path.split('/')[-1]}
                
                if file_ext == 'pgn':
                    result = self.ingest_pgn_data(content, metadata)
                elif file_ext == 'json':
                    result = self.ingest_json_data(content, metadata)
                elif file_ext == 'md':
                    result = self.ingest_markdown_data(content, metadata)
                
                if result.get('success'):
                    results['processed'] += 1
                    results['details'].append(f"Processed: {file_path}")
                else:
                    results['errors'] += 1
                    results['details'].append(f"Error processing {file_path}: {result.get('error', 'Unknown error')}")
            
            return results
            
        except Exception as e:
            return {
                'processed': 0,
                'errors': 1,
                'skipped': 0,
                'details': [f"Auto-ingest failed: {str(e)}"]
            }