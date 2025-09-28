#!/usr/bin/env python3
"""
Data Integrity Verification Suite
Comprehensive validation of ingested data in BigQuery
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
import chess.pgn
import io

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from google.cloud import bigquery
    from ingest_layer import BigQueryManager
    BIGQUERY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: BigQuery dependencies not available: {e}")
    BIGQUERY_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataIntegrityVerifier:
    """Comprehensive data integrity verification for chess engine metrics"""
    
    def __init__(self):
        """Initialize the data integrity verifier"""
        if not BIGQUERY_AVAILABLE:
            raise RuntimeError("BigQuery dependencies not available")
            
        # Get project ID from environment or config
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'chess-engine-analytics')
        
        self.bq_manager = BigQueryManager(project_id)
        self.bq_client = bigquery.Client()
        self.project_id = self.bq_client.project
        self.dataset_id = 'chess_engine_metrics'
        
        # Verification results
        self.verification_results = {
            'timestamp': datetime.now().isoformat(),
            'tables': {},
            'cross_table_checks': {},
            'data_quality': {},
            'anomalies': [],
            'summary': {}
        }
    
    def verify_table_structure(self, table_name: str) -> Dict[str, Any]:
        """Verify table schema and basic structure"""
        logger.info(f"🔍 Verifying table structure: {table_name}")
        
        results = {
            'exists': False,
            'schema': [],
            'row_count': 0,
            'size_mb': 0,
            'created': None,
            'modified': None
        }
        
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"
            table = self.bq_client.get_table(table_ref)
            
            results['exists'] = True
            results['schema'] = [{'name': field.name, 'type': field.field_type, 'mode': field.mode} 
                               for field in table.schema]
            results['row_count'] = table.num_rows
            results['size_mb'] = round(table.num_bytes / (1024 * 1024), 2)
            results['created'] = table.created.isoformat() if table.created else None
            results['modified'] = table.modified.isoformat() if table.modified else None
            
            logger.info(f"  ✅ Table exists: {results['row_count']} rows, {results['size_mb']} MB")
            
        except Exception as e:
            logger.error(f"  ❌ Table verification failed: {str(e)}")
            results['error'] = str(e)
            
        return results
    
    def verify_pgn_games_data(self) -> Dict[str, Any]:
        """Verify PGN games data integrity"""
        logger.info("🎯 Verifying PGN games data integrity")
        
        results = {
            'total_games': 0,
            'date_range': {},
            'engines': {},
            'results_distribution': {},
            'move_count_stats': {},
            'time_control_analysis': {},
            'data_quality_issues': []
        }
        
        try:
            # Basic stats query
            basic_query = """
            SELECT 
                COUNT(*) as total_games,
                MIN(game_date) as earliest_date,
                MAX(game_date) as latest_date,
                AVG(move_count) as avg_moves,
                MIN(move_count) as min_moves,
                MAX(move_count) as max_moves,
                STDDEV(move_count) as stddev_moves
            FROM `{}.{}.pgn_games`
            """.format(self.project_id, self.dataset_id)
            
            basic_stats = list(self.bq_client.query(basic_query).result())[0]
            
            results['total_games'] = basic_stats['total_games']
            results['date_range'] = {
                'earliest': basic_stats['earliest_date'].isoformat() if basic_stats['earliest_date'] else None,
                'latest': basic_stats['latest_date'].isoformat() if basic_stats['latest_date'] else None
            }
            results['move_count_stats'] = {
                'average': round(basic_stats['avg_moves'], 2) if basic_stats['avg_moves'] else 0,
                'minimum': basic_stats['min_moves'] or 0,
                'maximum': basic_stats['max_moves'] or 0,
                'std_dev': round(basic_stats['stddev_moves'], 2) if basic_stats['stddev_moves'] else 0
            }
            
            # Engine analysis
            engine_query = """
            SELECT 
                white_engine,
                black_engine,
                COUNT(*) as game_count
            FROM `{}.{}.pgn_games`
            GROUP BY white_engine, black_engine
            ORDER BY game_count DESC
            LIMIT 20
            """.format(self.project_id, self.dataset_id)
            
            engine_pairs = list(self.bq_client.query(engine_query).result())
            results['engines'] = {
                'top_matchups': [(row['white_engine'], row['black_engine'], row['game_count']) 
                               for row in engine_pairs]
            }
            
            # Results distribution
            results_query = """
            SELECT 
                result,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
            FROM `{}.{}.pgn_games`
            GROUP BY result
            ORDER BY count DESC
            """.format(self.project_id, self.dataset_id)
            
            result_dist = list(self.bq_client.query(results_query).result())
            results['results_distribution'] = {
                row['result']: {'count': row['count'], 'percentage': row['percentage']}
                for row in result_dist
            }
            
            # Data quality checks
            quality_query = """
            SELECT
                SUM(CASE WHEN white_engine IS NULL OR white_engine = '' THEN 1 ELSE 0 END) as missing_white_engine,
                SUM(CASE WHEN black_engine IS NULL OR black_engine = '' THEN 1 ELSE 0 END) as missing_black_engine,
                SUM(CASE WHEN result IS NULL OR result = '' THEN 1 ELSE 0 END) as missing_result,
                SUM(CASE WHEN move_count <= 0 THEN 1 ELSE 0 END) as invalid_move_count,
                SUM(CASE WHEN game_date IS NULL THEN 1 ELSE 0 END) as missing_date,
                SUM(CASE WHEN moves_text IS NULL OR moves_text = '' THEN 1 ELSE 0 END) as missing_moves
            FROM `{}.{}.pgn_games`
            """.format(self.project_id, self.dataset_id)
            
            quality_stats = list(self.bq_client.query(quality_query).result())[0]
            for field, count in quality_stats.items():
                if count > 0:
                    results['data_quality_issues'].append({
                        'issue': field,
                        'count': count,
                        'percentage': round(count * 100.0 / results['total_games'], 2)
                    })
            
            logger.info(f"  ✅ Verified {results['total_games']} games")
            
        except Exception as e:
            logger.error(f"  ❌ PGN verification failed: {str(e)}")
            results['error'] = str(e)
            
        return results
    
    def verify_analysis_results_data(self) -> Dict[str, Any]:
        """Verify analysis results data integrity"""
        logger.info("📊 Verifying analysis results data integrity")
        
        results = {
            'total_records': 0,
            'file_types': {},
            'date_range': {},
            'content_analysis': {},
            'data_quality_issues': []
        }
        
        try:
            # Basic stats
            basic_query = """
            SELECT 
                COUNT(*) as total_records,
                MIN(created_at) as earliest_date,
                MAX(created_at) as latest_date,
                COUNT(DISTINCT source_file) as unique_files
            FROM `{}.{}.analysis_results`
            """.format(self.project_id, self.dataset_id)
            
            basic_stats = list(self.bq_client.query(basic_query).result())[0]
            
            results['total_records'] = basic_stats['total_records']
            results['date_range'] = {
                'earliest': basic_stats['earliest_date'].isoformat() if basic_stats['earliest_date'] else None,
                'latest': basic_stats['latest_date'].isoformat() if basic_stats['latest_date'] else None
            }
            results['unique_files'] = basic_stats['unique_files']
            
            # File type analysis
            file_type_query = """
            SELECT 
                REGEXP_EXTRACT(source_file, r'\\.([^.]+)$') as file_extension,
                COUNT(*) as count
            FROM `{}.{}.analysis_results`
            GROUP BY file_extension
            ORDER BY count DESC
            """.format(self.project_id, self.dataset_id)
            
            file_types = list(self.bq_client.query(file_type_query).result())
            results['file_types'] = {
                row['file_extension'] or 'unknown': row['count']
                for row in file_types
            }
            
            # Content size analysis
            content_query = """
            SELECT 
                AVG(LENGTH(content)) as avg_content_length,
                MIN(LENGTH(content)) as min_content_length,
                MAX(LENGTH(content)) as max_content_length,
                SUM(CASE WHEN content IS NULL OR content = '' THEN 1 ELSE 0 END) as empty_content_count
            FROM `{}.{}.analysis_results`
            """.format(self.project_id, self.dataset_id)
            
            content_stats = list(self.bq_client.query(content_query).result())[0]
            results['content_analysis'] = {
                'avg_length': round(content_stats['avg_content_length'], 2) if content_stats['avg_content_length'] else 0,
                'min_length': content_stats['min_content_length'] or 0,
                'max_length': content_stats['max_content_length'] or 0,
                'empty_count': content_stats['empty_content_count'] or 0
            }
            
            if results['content_analysis']['empty_count'] > 0:
                results['data_quality_issues'].append({
                    'issue': 'empty_content',
                    'count': results['content_analysis']['empty_count'],
                    'percentage': round(results['content_analysis']['empty_count'] * 100.0 / results['total_records'], 2)
                })
            
            logger.info(f"  ✅ Verified {results['total_records']} analysis records")
            
        except Exception as e:
            logger.error(f"  ❌ Analysis results verification failed: {str(e)}")
            results['error'] = str(e)
            
        return results
    
    def verify_documentation_data(self) -> Dict[str, Any]:
        """Verify documentation data integrity"""
        logger.info("📚 Verifying documentation data integrity")
        
        results = {
            'total_documents': 0,
            'document_types': {},
            'date_range': {},
            'content_analysis': {},
            'data_quality_issues': []
        }
        
        try:
            # Basic stats
            basic_query = """
            SELECT 
                COUNT(*) as total_documents,
                MIN(created_at) as earliest_date,
                MAX(created_at) as latest_date,
                COUNT(DISTINCT source_file) as unique_files
            FROM `{}.{}.documentation`
            """.format(self.project_id, self.dataset_id)
            
            basic_stats = list(self.bq_client.query(basic_query).result())[0]
            
            results['total_documents'] = basic_stats['total_documents']
            results['date_range'] = {
                'earliest': basic_stats['earliest_date'].isoformat() if basic_stats['earliest_date'] else None,
                'latest': basic_stats['latest_date'].isoformat() if basic_stats['latest_date'] else None
            }
            results['unique_files'] = basic_stats['unique_files']
            
            # Document type analysis
            type_query = """
            SELECT 
                document_type,
                COUNT(*) as count
            FROM `{}.{}.documentation`
            GROUP BY document_type
            ORDER BY count DESC
            """.format(self.project_id, self.dataset_id)
            
            doc_types = list(self.bq_client.query(type_query).result())
            results['document_types'] = {
                row['document_type'] or 'unknown': row['count']
                for row in doc_types
            }
            
            # Content analysis
            content_query = """
            SELECT 
                AVG(LENGTH(content)) as avg_content_length,
                MIN(LENGTH(content)) as min_content_length,
                MAX(LENGTH(content)) as max_content_length,
                SUM(CASE WHEN content IS NULL OR content = '' THEN 1 ELSE 0 END) as empty_content_count,
                SUM(CASE WHEN title IS NULL OR title = '' THEN 1 ELSE 0 END) as missing_title_count
            FROM `{}.{}.documentation`
            """.format(self.project_id, self.dataset_id)
            
            content_stats = list(self.bq_client.query(content_query).result())[0]
            results['content_analysis'] = {
                'avg_length': round(content_stats['avg_content_length'], 2) if content_stats['avg_content_length'] else 0,
                'min_length': content_stats['min_content_length'] or 0,
                'max_length': content_stats['max_content_length'] or 0,
                'empty_count': content_stats['empty_content_count'] or 0,
                'missing_titles': content_stats['missing_title_count'] or 0
            }
            
            # Quality issues
            if results['content_analysis']['empty_count'] > 0:
                results['data_quality_issues'].append({
                    'issue': 'empty_content',
                    'count': results['content_analysis']['empty_count']
                })
            
            if results['content_analysis']['missing_titles'] > 0:
                results['data_quality_issues'].append({
                    'issue': 'missing_titles',
                    'count': results['content_analysis']['missing_titles']
                })
            
            logger.info(f"  ✅ Verified {results['total_documents']} documents")
            
        except Exception as e:
            logger.error(f"  ❌ Documentation verification failed: {str(e)}")
            results['error'] = str(e)
            
        return results
    
    def verify_cross_table_consistency(self) -> Dict[str, Any]:
        """Verify consistency across tables"""
        logger.info("🔗 Verifying cross-table consistency")
        
        results = {
            'date_consistency': {},
            'file_source_consistency': {},
            'engine_name_consistency': {}
        }
        
        try:
            # Date range consistency
            date_query = """
            SELECT 
                'pgn_games' as table_name,
                MIN(game_date) as min_date,
                MAX(game_date) as max_date
            FROM `{}.{}.pgn_games`
            UNION ALL
            SELECT 
                'analysis_results' as table_name,
                MIN(DATE(created_at)) as min_date,
                MAX(DATE(created_at)) as max_date
            FROM `{}.{}.analysis_results`
            UNION ALL
            SELECT 
                'documentation' as table_name,
                MIN(DATE(created_at)) as min_date,
                MAX(DATE(created_at)) as max_date
            FROM `{}.{}.documentation`
            """.format(self.project_id, self.dataset_id)
            
            date_ranges = list(self.bq_client.query(date_query).result())
            for row in date_ranges:
                results['date_consistency'][row['table_name']] = {
                    'min_date': row['min_date'].isoformat() if row['min_date'] else None,
                    'max_date': row['max_date'].isoformat() if row['max_date'] else None
                }
            
            logger.info("  ✅ Cross-table consistency verified")
            
        except Exception as e:
            logger.error(f"  ❌ Cross-table verification failed: {str(e)}")
            results['error'] = str(e)
            
        return results
    
    def sample_data_validation(self) -> Dict[str, Any]:
        """Sample and validate specific data records"""
        logger.info("🎲 Performing sample data validation")
        
        results = {
            'pgn_sample_validation': {},
            'json_sample_validation': {},
            'sample_issues': []
        }
        
        try:
            # Sample PGN games for detailed validation
            pgn_sample_query = """
            SELECT source_file, moves_text, white_engine, black_engine, result, move_count
            FROM `{}.{}.pgn_games`
            WHERE moves_text IS NOT NULL AND moves_text != ''
            ORDER BY RAND()
            LIMIT 5
            """.format(self.project_id, self.dataset_id)
            
            pgn_samples = list(self.bq_client.query(pgn_sample_query).result())
            valid_pgn_count = 0
            
            for i, sample in enumerate(pgn_samples):
                try:
                    # Try to parse the PGN
                    pgn_io = io.StringIO(sample['moves_text'])
                    game = chess.pgn.read_game(pgn_io)
                    
                    if game:
                        # Count actual moves
                        actual_moves = len(list(game.mainline_moves()))
                        recorded_moves = sample['move_count']
                        
                        if abs(actual_moves - recorded_moves) <= 1:  # Allow small discrepancy
                            valid_pgn_count += 1
                        else:
                            results['sample_issues'].append({
                                'type': 'move_count_mismatch',
                                'file': sample['source_file'],
                                'recorded': recorded_moves,
                                'actual': actual_moves
                            })
                    else:
                        results['sample_issues'].append({
                            'type': 'unparseable_pgn',
                            'file': sample['source_file']
                        })
                        
                except Exception as e:
                    results['sample_issues'].append({
                        'type': 'pgn_parsing_error',
                        'file': sample['source_file'],
                        'error': str(e)
                    })
            
            results['pgn_sample_validation'] = {
                'samples_tested': len(pgn_samples),
                'valid_samples': valid_pgn_count,
                'validation_rate': round(valid_pgn_count * 100.0 / len(pgn_samples), 2) if pgn_samples else 0
            }
            
            # Sample JSON analysis results
            json_sample_query = """
            SELECT source_file, content
            FROM `{}.{}.analysis_results`
            WHERE content IS NOT NULL AND content != ''
            ORDER BY RAND()
            LIMIT 5
            """.format(self.project_id, self.dataset_id)
            
            json_samples = list(self.bq_client.query(json_sample_query).result())
            valid_json_count = 0
            
            for sample in json_samples:
                try:
                    json.loads(sample['content'])
                    valid_json_count += 1
                except json.JSONDecodeError as e:
                    results['sample_issues'].append({
                        'type': 'invalid_json',
                        'file': sample['source_file'],
                        'error': str(e)
                    })
            
            results['json_sample_validation'] = {
                'samples_tested': len(json_samples),
                'valid_samples': valid_json_count,
                'validation_rate': round(valid_json_count * 100.0 / len(json_samples), 2) if json_samples else 0
            }
            
            logger.info(f"  ✅ Sample validation completed")
            
        except Exception as e:
            logger.error(f"  ❌ Sample validation failed: {str(e)}")
            results['error'] = str(e)
            
        return results
    
    def generate_verification_report(self) -> str:
        """Generate comprehensive verification report"""
        logger.info("📋 Generating verification report")
        
        # Run all verifications
        tables = ['pgn_games', 'analysis_results', 'documentation']
        
        for table in tables:
            self.verification_results['tables'][table] = self.verify_table_structure(table)
        
        self.verification_results['data_quality']['pgn_games'] = self.verify_pgn_games_data()
        self.verification_results['data_quality']['analysis_results'] = self.verify_analysis_results_data()
        self.verification_results['data_quality']['documentation'] = self.verify_documentation_data()
        self.verification_results['cross_table_checks'] = self.verify_cross_table_consistency()
        self.verification_results['sample_validation'] = self.sample_data_validation()
        
        # Generate summary
        total_records = sum([
            self.verification_results['tables'][table].get('row_count', 0) 
            for table in tables if 'error' not in self.verification_results['tables'][table]
        ])
        
        total_size_mb = sum([
            self.verification_results['tables'][table].get('size_mb', 0) 
            for table in tables if 'error' not in self.verification_results['tables'][table]
        ])
        
        self.verification_results['summary'] = {
            'total_records': total_records,
            'total_size_mb': total_size_mb,
            'tables_verified': len([t for t in tables if self.verification_results['tables'][t].get('exists', False)]),
            'verification_timestamp': datetime.now().isoformat()
        }
        
        # Save report
        report_filename = f"data_integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(os.path.dirname(__file__), report_filename)
        
        with open(report_path, 'w') as f:
            json.dump(self.verification_results, f, indent=2, default=str)
        
        logger.info(f"📄 Verification report saved: {report_path}")
        return report_path

def main():
    """Main verification function"""
    logger.info("🚀 Starting Data Integrity Verification")
    logger.info("=" * 50)
    
    try:
        verifier = DataIntegrityVerifier()
        report_path = verifier.generate_verification_report()
        
        # Print summary
        print("\n" + "=" * 50)
        print("DATA INTEGRITY VERIFICATION SUMMARY")
        print("=" * 50)
        
        summary = verifier.verification_results['summary']
        print(f"Total Records Verified: {summary['total_records']:,}")
        print(f"Total Data Size: {summary['total_size_mb']:.2f} MB")
        print(f"Tables Verified: {summary['tables_verified']}")
        
        # Print table details
        for table_name, table_info in verifier.verification_results['tables'].items():
            if table_info.get('exists'):
                print(f"\n{table_name.upper()}:")
                print(f"  Rows: {table_info['row_count']:,}")
                print(f"  Size: {table_info['size_mb']:.2f} MB")
                
                # Print data quality for this table
                if table_name in verifier.verification_results['data_quality']:
                    quality = verifier.verification_results['data_quality'][table_name]
                    if 'data_quality_issues' in quality and quality['data_quality_issues']:
                        print(f"  ⚠️  Quality Issues: {len(quality['data_quality_issues'])}")
                        for issue in quality['data_quality_issues']:
                            print(f"    - {issue['issue']}: {issue['count']} records")
                    else:
                        print(f"  ✅ No quality issues detected")
        
        # Print sample validation results
        sample_validation = verifier.verification_results.get('sample_validation', {})
        if sample_validation:
            print(f"\nSAMPLE VALIDATION:")
            pgn_val = sample_validation.get('pgn_sample_validation', {})
            if pgn_val:
                print(f"  PGN Validation Rate: {pgn_val.get('validation_rate', 0)}%")
            
            json_val = sample_validation.get('json_sample_validation', {})
            if json_val:
                print(f"  JSON Validation Rate: {json_val.get('validation_rate', 0)}%")
            
            issues = sample_validation.get('sample_issues', [])
            if issues:
                print(f"  ⚠️  Sample Issues: {len(issues)}")
                for issue in issues[:5]:  # Show first 5 issues
                    print(f"    - {issue['type']}: {issue.get('file', 'N/A')}")
        
        print(f"\n📄 Detailed report: {report_path}")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)