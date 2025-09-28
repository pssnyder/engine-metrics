#!/usr/bin/env python3
"""
Data Structure Verification - Check schemas and sample data
"""

import os
import sys

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_data_structure():
    """Check table structures and sample data"""
    
    try:
        from google.cloud import bigquery
        
        project_id = 'chess-engine-metrics-agent'
        client = bigquery.Client(project=project_id)
        
        print("🔍 Data Structure Verification")
        print("=" * 50)
        
        # Check table schemas
        tables = ['pgn_games', 'analysis_results', 'documentation']
        
        for table_name in tables:
            print(f"\n📋 {table_name.upper()} TABLE:")
            try:
                table_ref = f"{project_id}.chess_engine_data_lake.{table_name}"
                table = client.get_table(table_ref)
                
                print(f"  Rows: {table.num_rows:,}")
                print(f"  Size: {table.num_bytes / (1024*1024):.1f} MB")
                print(f"  Schema fields:")
                
                for field in table.schema[:5]:  # Show first 5 fields
                    print(f"    - {field.name}: {field.field_type} ({field.mode})")
                
                if len(table.schema) > 5:
                    print(f"    ... and {len(table.schema)-5} more fields")
                
                # Sample one record
                sample_query = f"SELECT * FROM `{table_ref}` LIMIT 1"
                sample = list(client.query(sample_query).result())
                
                if sample:
                    print("  Sample record keys:", list(sample[0].keys())[:8])
                
            except Exception as e:
                print(f"  ❌ Error checking {table_name}: {str(e)[:60]}...")
        
        # Check PGN games in detail
        print(f"\n🎯 PGN GAMES ANALYSIS:")
        try:
            pgn_analysis_query = f"""
            SELECT 
                COUNT(*) as total_games,
                COUNT(DISTINCT CONCAT(white_player, '_vs_', black_player)) as unique_matchups,
                MIN(LENGTH(pgn_text)) as min_pgn_length,
                MAX(LENGTH(pgn_text)) as max_pgn_length,
                AVG(LENGTH(pgn_text)) as avg_pgn_length
            FROM `{project_id}.chess_engine_data_lake.pgn_games`
            WHERE pgn_text IS NOT NULL
            """
            
            analysis = list(client.query(pgn_analysis_query).result())
            if analysis:
                stats = analysis[0]
                print(f"  Total games: {stats['total_games']:,}")
                print(f"  Unique matchups: {stats['unique_matchups']:,}")
                print(f"  PGN length range: {stats['min_pgn_length']}-{stats['max_pgn_length']} chars")
                print(f"  Avg PGN length: {stats['avg_pgn_length']:.0f} chars")
                
        except Exception as e:
            print(f"  ❌ PGN analysis failed: {str(e)[:60]}...")
        
        # Check analysis results
        print(f"\n📊 ANALYSIS RESULTS:")
        try:
            analysis_query = f"""
            SELECT 
                COUNT(*) as total_files,
                COUNT(DISTINCT source_file) as unique_files,
                MIN(LENGTH(content)) as min_content_length,
                MAX(LENGTH(content)) as max_content_length
            FROM `{project_id}.chess_engine_data_lake.analysis_results`
            WHERE content IS NOT NULL
            """
            
            analysis = list(client.query(analysis_query).result())
            if analysis:
                stats = analysis[0]
                print(f"  Total records: {stats['total_files']:,}")
                print(f"  Unique files: {stats['unique_files']:,}")
                print(f"  Content length range: {stats['min_content_length']}-{stats['max_content_length']} chars")
                
        except Exception as e:
            print(f"  ❌ Analysis results check failed: {str(e)[:60]}...")
        
        print(f"\n✅ Data structure verification complete!")
        return True
        
    except ImportError as e:
        print(f"❌ BigQuery not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Structure check failed: {e}")
        return False

if __name__ == "__main__":
    success = check_data_structure()
    sys.exit(0 if success else 1)