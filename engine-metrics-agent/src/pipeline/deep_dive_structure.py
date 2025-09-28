#!/usr/bin/env python3
"""
Data Structure Deep Dive
Understand why row counts don't match record counts
"""

import os
import sys
from datetime import datetime

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def deep_dive_structure():
    """Deep dive into actual data structure"""
    
    try:
        from google.cloud import bigquery
        
        project_id = 'chess-engine-metrics-agent'
        client = bigquery.Client(project=project_id)
        
        print("🔬 DATA STRUCTURE DEEP DIVE")
        print("=" * 50)
        
        # 1. Check pgn_games in detail
        print(f"\n1️⃣ PGN_GAMES TABLE ANALYSIS")
        print("-" * 35)
        
        try:
            # Count records by ingestion date
            ingestion_query = f"""
            SELECT 
                DATE(ingested_at) as ingestion_date,
                COUNT(*) as records,
                COUNT(DISTINCT game_id) as unique_game_ids,
                COUNT(DISTINCT source_file) as unique_files
            FROM `{project_id}.chess_engine_data_lake.pgn_games`
            WHERE ingested_at IS NOT NULL
            GROUP BY DATE(ingested_at)
            ORDER BY ingestion_date DESC
            LIMIT 5
            """
            
            results = list(client.query(ingestion_query).result())
            print(f"  📅 Records by Ingestion Date:")
            total_records = 0
            for result in results:
                total_records += result['records']
                print(f"    {result['ingestion_date']}: {result['records']:>6,} records, {result['unique_game_ids']:>6,} unique IDs, {result['unique_files']:>3,} files")
            
            print(f"  📊 Total Records Found: {total_records:,}")
            
            # Check for duplicate game_ids
            duplicate_query = f"""
            SELECT 
                game_id,
                COUNT(*) as count
            FROM `{project_id}.chess_engine_data_lake.pgn_games`
            GROUP BY game_id
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 5
            """
            
            duplicates = list(client.query(duplicate_query).result())
            if duplicates:
                print(f"  ⚠️  Duplicate Game IDs Found:")
                for dup in duplicates:
                    print(f"    {dup['game_id'][:50]}: {dup['count']} times")
            else:
                print(f"  ✅ No duplicate game_ids found")
                
        except Exception as e:
            print(f"  ❌ PGN analysis failed: {str(e)}")
        
        # 2. Sample actual records
        print(f"\n2️⃣ SAMPLE RECORDS")
        print("-" * 25)
        
        for table_name in ['pgn_games', 'analysis_results', 'documentation']:
            print(f"\n  📋 {table_name.upper()} Sample:")
            try:
                sample_query = f"""
                SELECT *
                FROM `{project_id}.chess_engine_data_lake.{table_name}`
                WHERE ingested_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
                ORDER BY ingested_at DESC
                LIMIT 2
                """
                
                samples = list(client.query(sample_query).result())
                for i, sample in enumerate(samples):
                    print(f"    Record {i+1}:")
                    sample_dict = dict(sample)
                    for key, value in list(sample_dict.items())[:5]:  # First 5 fields
                        value_str = str(value)[:50] if value else "NULL"
                        print(f"      {key:<20}: {value_str}")
                    print(f"      ... ({len(sample_dict)-5} more fields)")
                    
            except Exception as e:
                print(f"    ❌ Sample failed: {str(e)[:50]}...")
        
        # 3. Verify our expected totals
        print(f"\n3️⃣ TOTAL VERIFICATION")
        print("-" * 30)
        
        table_totals = {}
        grand_total = 0
        
        for table_name in ['pgn_games', 'analysis_results', 'documentation']:
            try:
                count_query = f"""
                SELECT COUNT(*) as total
                FROM `{project_id}.chess_engine_data_lake.{table_name}`
                """
                
                result = list(client.query(count_query).result())
                count = result[0]['total'] if result else 0
                table_totals[table_name] = count
                grand_total += count
                
                print(f"  📊 {table_name:<18}: {count:>8,} records")
                
            except Exception as e:
                print(f"  ❌ {table_name:<18}: Error")
        
        print(f"  {'='*30}")
        print(f"  📊 {'GRAND TOTAL':<18}: {grand_total:>8,} records")
        
        # 4. Expected vs Actual Analysis
        print(f"\n4️⃣ EXPECTED vs ACTUAL")
        print("-" * 30)
        
        expected = {
            'pgn_games': 29185,
            'analysis_results': 2352,
            'documentation': 122
        }
        
        print(f"  {'Table':<18} | {'Expected':<10} | {'Actual':<10} | {'Status'}")
        print(f"  {'-'*18} | {'-'*10} | {'-'*10} | {'-'*10}")
        
        for table, exp_count in expected.items():
            actual_count = table_totals.get(table, 0)
            if actual_count >= exp_count * 0.9:  # Within 10%
                status = "✅ MATCH"
            elif actual_count > 0:
                status = f"⚠️ {actual_count/exp_count*100:.0f}%"
            else:
                status = "❌ MISSING"
            
            print(f"  {table:<18} | {exp_count:<10,} | {actual_count:<10,} | {status}")
        
        expected_total = sum(expected.values())
        match_percentage = grand_total / expected_total * 100 if expected_total > 0 else 0
        
        print(f"  {'='*18} | {'='*10} | {'='*10} | {'='*10}")
        print(f"  {'TOTALS':<18} | {expected_total:<10,} | {grand_total:<10,} | {match_percentage:.0f}%")
        
        # 5. Conclusion
        print(f"\n5️⃣ CONCLUSION")
        print("-" * 20)
        
        if match_percentage >= 90:
            print(f"  🎉 DATA INTEGRITY: EXCELLENT!")
            print(f"  📊 Match Rate: {match_percentage:.1f}%")
            print(f"  ✅ All expected data appears to be present")
        elif match_percentage >= 70:
            print(f"  ⚠️  DATA INTEGRITY: GOOD")
            print(f"  📊 Match Rate: {match_percentage:.1f}%") 
            print(f"  🔍 Some data may be missing - investigate further")
        else:
            print(f"  ❌ DATA INTEGRITY: POOR")
            print(f"  📊 Match Rate: {match_percentage:.1f}%")
            print(f"  🚨 Major data loss detected - re-ingestion needed")
        
        return match_percentage >= 70
        
    except ImportError as e:
        print(f"❌ BigQuery not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Deep dive failed: {e}")
        return False

if __name__ == "__main__":
    success = deep_dive_structure()
    sys.exit(0 if success else 1)