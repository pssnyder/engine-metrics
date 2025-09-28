#!/usr/bin/env python3
"""
Simple Data Verification - Basic Health Check
"""

import os
import sys
import json
from datetime import datetime

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def simple_verification():
    """Simple verification of data counts"""
    
    try:
        from google.cloud import bigquery
        
        project_id = 'chess-engine-metrics-agent'
        client = bigquery.Client(project=project_id)
        
        print("🚀 Chess Engine Data Verification")
        print("=" * 40)
        
        tables = ['pgn_games', 'analysis_results', 'documentation']
        results = {}
        
        for table_name in tables:
            try:
                query = f"""
                SELECT COUNT(*) as count
                FROM `{project_id}.chess_engine_data_lake.{table_name}`
                """
                
                result = list(client.query(query).result())
                count = result[0]['count']
                results[table_name] = count
                
                print(f"✅ {table_name:<20}: {count:,} records")
                
            except Exception as e:
                print(f"❌ {table_name:<20}: Error - {str(e)[:50]}...")
                results[table_name] = 0
        
        # Quick PGN sample
        try:
            sample_query = f"""
            SELECT white_engine, black_engine, result, move_count
            FROM `{project_id}.chess_engine_data_lake.pgn_games`
            ORDER BY game_date DESC
            LIMIT 3
            """
            
            samples = list(client.query(sample_query).result())
            print(f"\n🎯 Recent Games Sample:")
            for sample in samples:
                print(f"   {sample['white_engine']} vs {sample['black_engine']} = {sample['result']} ({sample['move_count']} moves)")
                
        except Exception as e:
            print(f"❌ Sample query failed: {str(e)[:50]}...")
        
        # Summary
        total_records = sum(results.values())
        print(f"\n📊 TOTAL RECORDS: {total_records:,}")
        print(f"📅 Verification: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if total_records > 25000:  # We expect ~30K records
            print("🎉 Data integrity looks good!")
            return True
        else:
            print("⚠️  Lower than expected record count")
            return False
            
    except ImportError as e:
        print(f"❌ BigQuery not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    success = simple_verification()
    sys.exit(0 if success else 1)