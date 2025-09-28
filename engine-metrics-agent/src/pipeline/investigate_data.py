#!/usr/bin/env python3
"""
Data Location Investigation
Find where the 30,244 records from our batch ingestion actually went
"""

import os
import sys
from datetime import datetime

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def investigate_data_location():
    """Investigate where our ingested data actually is"""
    
    try:
        from google.cloud import bigquery
        
        project_id = 'chess-engine-metrics-agent'
        client = bigquery.Client(project=project_id)
        
        print("🔍 DATA LOCATION INVESTIGATION")
        print("=" * 50)
        print(f"📅 Investigation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Target: Find 30,244 records from batch ingestion")
        
        # 1. List all datasets in project
        print(f"\n1️⃣ DATASETS IN PROJECT")
        print("-" * 30)
        
        datasets = list(client.list_datasets())
        if datasets:
            for dataset in datasets:
                print(f"  📦 {dataset.dataset_id}")
                
                # Check tables in each dataset
                dataset_ref = client.dataset(dataset.dataset_id)
                tables = list(client.list_tables(dataset_ref))
                
                if tables:
                    total_rows = 0
                    for table in tables:
                        table_obj = client.get_table(table)
                        rows = table_obj.num_rows
                        size_mb = table_obj.num_bytes / (1024*1024)
                        total_rows += rows
                        print(f"    📋 {table.table_id:<20}: {rows:>8,} rows ({size_mb:>6.1f} MB)")
                    
                    print(f"    {'='*35}")
                    print(f"    📊 Dataset Total: {total_rows:>8,} rows")
                    
                    # Check if this might be our missing data
                    if total_rows > 20000:
                        print(f"    🎯 *** POTENTIAL MATCH - Large dataset found! ***")
                else:
                    print(f"    📋 (no tables)")
                    
                print()
        else:
            print("  ❌ No datasets found")
        
        # 2. Deep dive into chess_engine_data_lake
        print(f"\n2️⃣ DETAILED chess_engine_data_lake ANALYSIS")
        print("-" * 45)
        
        try:
            dataset_ref = client.dataset('chess_engine_data_lake')
            tables = list(client.list_tables(dataset_ref))
            
            for table in tables:
                print(f"\n  📋 TABLE: {table.table_id}")
                table_obj = client.get_table(table)
                
                print(f"    Rows: {table_obj.num_rows:,}")
                print(f"    Size: {table_obj.num_bytes / (1024*1024):.1f} MB")
                print(f"    Created: {table_obj.created}")
                print(f"    Modified: {table_obj.modified}")
                
                # Check recent ingestion
                if table_obj.num_rows > 0:
                    try:
                        recent_query = f"""
                        SELECT 
                            MIN(ingested_at) as earliest_ingestion,
                            MAX(ingested_at) as latest_ingestion,
                            COUNT(*) as total_records
                        FROM `{project_id}.chess_engine_data_lake.{table.table_id}`
                        WHERE ingested_at IS NOT NULL
                        """
                        
                        result = list(client.query(recent_query).result())
                        if result and result[0]['total_records']:
                            stats = result[0]
                            print(f"    Ingestion Period: {stats['earliest_ingestion']} to {stats['latest_ingestion']}")
                            print(f"    Records with timestamps: {stats['total_records']:,}")
                            
                            # Check if we have today's ingestion
                            today_query = f"""
                            SELECT COUNT(*) as today_count
                            FROM `{project_id}.chess_engine_data_lake.{table.table_id}`
                            WHERE DATE(ingested_at) = CURRENT_DATE()
                            """
                            
                            today_result = list(client.query(today_query).result())
                            if today_result:
                                today_count = today_result[0]['today_count']
                                print(f"    Today's ingestion: {today_count:,} records")
                                if today_count > 1000:
                                    print(f"    🎯 *** LARGE TODAY INGESTION - LIKELY OUR DATA! ***")
                    
                    except Exception as e:
                        print(f"    ⚠️ Could not check ingestion times: {str(e)[:50]}...")
        
        except Exception as e:
            print(f"  ❌ Error analyzing chess_engine_data_lake: {str(e)}")
        
        # 3. Check for alternative table names
        print(f"\n3️⃣ ALTERNATIVE TABLE NAME SEARCH")
        print("-" * 40)
        
        alternative_names = [
            'games', 'chess_games', 'pgn_data',
            'analyses', 'engine_analysis', 'analysis_data',
            'docs', 'documents', 'documentation_files'
        ]
        
        for dataset in datasets:
            dataset_ref = client.dataset(dataset.dataset_id)
            tables = list(client.list_tables(dataset_ref))
            
            for table in tables:
                table_name_lower = table.table_id.lower()
                for alt_name in alternative_names:
                    if alt_name in table_name_lower:
                        table_obj = client.get_table(table)
                        print(f"  🔍 Found similar: {dataset.dataset_id}.{table.table_id} ({table_obj.num_rows:,} rows)")
        
        # 4. Summary and recommendations
        print(f"\n4️⃣ INVESTIGATION SUMMARY")
        print("-" * 35)
        
        print(f"  📊 Expected Records: 30,244")
        print(f"  📊 Found Records: [TO BE DETERMINED]")
        print(f"  🎯 Recommendation: [TO BE DETERMINED]")
        
        print(f"\n{'='*50}")
        print(f"🔍 INVESTIGATION COMPLETE")
        
        return True
        
    except ImportError as e:
        print(f"❌ BigQuery not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        return False

if __name__ == "__main__":
    success = investigate_data_location()
    sys.exit(0 if success else 1)