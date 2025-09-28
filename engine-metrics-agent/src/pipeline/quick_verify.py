#!/usr/bin/env python3
"""
Quick Data Verification Script
Simple validation of our BigQuery data without complex dependencies
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_quick_verification():
    """Run quick data verification using existing BigQuery manager"""
    
    try:
        from google.cloud import bigquery
        
        # Initialize BigQuery client directly
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'chess-engine-metrics-agent')
        client = bigquery.Client(project=project_id)
        
        logger.info("🚀 Starting Quick Data Verification")
        logger.info("=" * 50)
        
        verification_results = {}
        
        # Test 1: Basic table existence and counts
        logger.info("📊 Checking table structures and counts...")
        
        tables = ['pgn_games', 'analysis_results', 'documentation']
        
        for table_name in tables:
            try:
                # Simple count query
                count_query = f"""
                SELECT COUNT(*) as row_count
                FROM `{project_id}.chess_engine_data_lake.{table_name}`
                """
                
                results = list(client.query(count_query).result())
                if results and len(results) > 0:
                    count = results[0]['row_count']
                    verification_results[table_name] = {
                        'exists': True,
                        'row_count': count,
                        'status': 'OK'
                    }
                    logger.info(f"  ✅ {table_name}: {count:,} records")
                else:
                    verification_results[table_name] = {
                        'exists': False,
                        'status': 'MISSING'
                    }
                    logger.warning(f"  ⚠️  {table_name}: No data returned")
                    
            except Exception as e:
                verification_results[table_name] = {
                    'exists': False,
                    'error': str(e),
                    'status': 'ERROR'
                }
                logger.error(f"  ❌ {table_name}: {str(e)}")
        
        # Test 2: Data quality checks for PGN games
        logger.info("\n🎯 Checking PGN games data quality...")
        try:
            pgn_quality_query = f"""
            SELECT 
                COUNT(*) as total_games,
                COUNT(DISTINCT white_engine) as unique_white_engines,
                COUNT(DISTINCT black_engine) as unique_black_engines,
                SUM(CASE WHEN result = '1-0' THEN 1 ELSE 0 END) as white_wins,
                SUM(CASE WHEN result = '0-1' THEN 1 ELSE 0 END) as black_wins,
                SUM(CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END) as draws,
                AVG(move_count) as avg_moves,
                MIN(game_date) as earliest_date,
                MAX(game_date) as latest_date
            FROM `{project_id}.chess_engine_data_lake.pgn_games`
            """
            
            pgn_results = list(client.query(pgn_quality_query).result())
            if pgn_results and len(pgn_results) > 0:
                stats = dict(pgn_results[0])
                verification_results['pgn_quality'] = stats
                
                logger.info(f"  📈 Total Games: {stats['total_games']:,}")
                logger.info(f"  🏆 White Wins: {stats['white_wins']:,} ({stats['white_wins']*100/stats['total_games']:.1f}%)")
                logger.info(f"  🏆 Black Wins: {stats['black_wins']:,} ({stats['black_wins']*100/stats['total_games']:.1f}%)")
                logger.info(f"  🤝 Draws: {stats['draws']:,} ({stats['draws']*100/stats['total_games']:.1f}%)")
                logger.info(f"  📅 Date Range: {stats['earliest_date']} to {stats['latest_date']}")
                logger.info(f"  🎮 Unique Engines: {max(stats['unique_white_engines'], stats['unique_black_engines'])}")
                logger.info(f"  📊 Avg Moves: {stats['avg_moves']:.1f}")
                
        except Exception as e:
            logger.error(f"  ❌ PGN quality check failed: {str(e)}")
            verification_results['pgn_quality'] = {'error': str(e)}
        
        # Test 3: Sample recent data
        logger.info("\n🔍 Sampling recent data...")
        try:
            sample_query = f"""
            SELECT 
                source_file,
                white_engine,
                black_engine,
                result,
                move_count,
                game_date
            FROM `{project_id}.chess_engine_data_lake.pgn_games`
            ORDER BY game_date DESC
            LIMIT 5
            """
            
            samples = [dict(row) for row in client.query(sample_query).result()]
            verification_results['recent_samples'] = samples
            
            logger.info("  📋 Recent Games:")
            for sample in samples:
                logger.info(f"    {sample['white_engine']} vs {sample['black_engine']} = {sample['result']} ({sample['move_count']} moves)")
                
        except Exception as e:
            logger.error(f"  ❌ Sample data check failed: {str(e)}")
            verification_results['recent_samples'] = {'error': str(e)}
        
        # Test 4: Engine analysis
        logger.info("\n🤖 Analyzing chess engines...")
        try:
            engine_query = f"""
            WITH engine_stats AS (
                SELECT 
                    white_engine as engine,
                    COUNT(*) as games_as_white,
                    SUM(CASE WHEN result = '1-0' THEN 1 ELSE 0 END) as wins_as_white,
                    SUM(CASE WHEN result = '0-1' THEN 1 ELSE 0 END) as losses_as_white,
                    SUM(CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END) as draws_as_white
                FROM `{project_id}.chess_engine_data_lake.pgn_games`
                GROUP BY white_engine
                UNION ALL
                SELECT 
                    black_engine as engine,
                    COUNT(*) as games_as_black,
                    SUM(CASE WHEN result = '0-1' THEN 1 ELSE 0 END) as wins_as_black,
                    SUM(CASE WHEN result = '1-0' THEN 1 ELSE 0 END) as losses_as_black,
                    SUM(CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END) as draws_as_black
                FROM `{project_id}.chess_engine_data_lake.pgn_games`
                GROUP BY black_engine
            )
            SELECT 
                engine,
                SUM(games_as_white + games_as_black) as total_games,
                SUM(wins_as_white + wins_as_black) as total_wins,
                ROUND(SUM(wins_as_white + wins_as_black) * 100.0 / SUM(games_as_white + games_as_black), 2) as win_rate
            FROM engine_stats
            GROUP BY engine
            ORDER BY total_games DESC
            LIMIT 10
            """
            
            engines = [dict(row) for row in client.query(engine_query).result()]
            verification_results['top_engines'] = engines
            
            logger.info("  🏆 Top Engines by Games Played:")
            for engine in engines:
                logger.info(f"    {engine['engine']}: {engine['total_games']} games, {engine['win_rate']:.1f}% win rate")
                
        except Exception as e:
            logger.error(f"  ❌ Engine analysis failed: {str(e)}")
            verification_results['top_engines'] = {'error': str(e)}
        
        # Save verification results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"quick_verification_{timestamp}.json"
        results_path = os.path.join(os.path.dirname(__file__), results_file)
        
        with open(results_path, 'w') as f:
            json.dump(verification_results, f, indent=2, default=str)
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 50)
        
        total_records = sum([
            result.get('row_count', 0) 
            for result in verification_results.values() 
            if isinstance(result, dict) and 'row_count' in result
        ])
        
        healthy_tables = sum([
            1 for result in verification_results.values() 
            if isinstance(result, dict) and result.get('status') == 'OK'
        ])
        
        logger.info(f"📊 Total Records: {total_records:,}")
        logger.info(f"✅ Healthy Tables: {healthy_tables}/3")
        logger.info(f"📄 Detailed Results: {results_path}")
        
        if healthy_tables == 3:
            logger.info("🎉 All systems operational! Data integrity looks good.")
            return True
        else:
            logger.warning("⚠️  Some issues detected. Check the detailed report.")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Cannot import required modules: {e}")
        logger.info("💡 Make sure you're in the correct environment with BigQuery dependencies")
        return False
    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        return False

def main():
    """Main function"""
    success = run_quick_verification()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())