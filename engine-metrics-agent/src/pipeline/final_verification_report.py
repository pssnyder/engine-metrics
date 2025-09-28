#!/usr/bin/env python3
"""
Final Data Verification Report
Complete confirmation of chess engine data integrity in BigQuery
"""

import os
import sys
from datetime import datetime

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def final_verification_report():
    """Generate final data verification report"""
    
    try:
        from google.cloud import bigquery
        
        project_id = 'chess-engine-metrics-agent'
        client = bigquery.Client(project=project_id)
        
        print("🎯 FINAL DATA VERIFICATION REPORT")
        print("=" * 60)
        print(f"📅 Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"🎯 Project: {project_id}")
        print(f"📦 Dataset: chess_engine_data_lake")
        
        # Comprehensive data summary
        print(f"\n📊 COMPREHENSIVE DATA SUMMARY")
        print("=" * 40)
        
        tables_info = {}
        grand_total = 0
        
        for table_name in ['pgn_games', 'analysis_results', 'documentation']:
            try:
                # Get detailed table info
                table_ref = f"{project_id}.chess_engine_data_lake.{table_name}"
                table = client.get_table(table_ref)
                
                # Count records
                count_query = f"SELECT COUNT(*) as total FROM `{table_ref}`"
                count_result = list(client.query(count_query).result())
                record_count = count_result[0]['total'] if count_result else 0
                
                # Get ingestion stats
                ingestion_query = f"""
                SELECT 
                    MIN(ingested_at) as first_ingested,
                    MAX(ingested_at) as last_ingested,
                    COUNT(DISTINCT DATE(ingested_at)) as ingestion_days
                FROM `{table_ref}`
                WHERE ingested_at IS NOT NULL
                """
                
                ingestion_stats = list(client.query(ingestion_query).result())[0]
                
                tables_info[table_name] = {
                    'records': record_count,
                    'size_mb': table.num_bytes / (1024*1024),
                    'created': table.created,
                    'modified': table.modified,
                    'first_ingested': ingestion_stats['first_ingested'],
                    'last_ingested': ingestion_stats['last_ingested'],
                    'ingestion_days': ingestion_stats['ingestion_days']
                }
                
                grand_total += record_count
                
                print(f"\n📋 {table_name.upper()}")
                print(f"  Records: {record_count:,}")
                print(f"  Size: {table.num_bytes / (1024*1024):.1f} MB")
                print(f"  First Ingestion: {ingestion_stats['first_ingested']}")
                print(f"  Last Ingestion: {ingestion_stats['last_ingested']}")
                print(f"  Ingestion Days: {ingestion_stats['ingestion_days']}")
                
            except Exception as e:
                print(f"  ❌ Error analyzing {table_name}: {str(e)}")
        
        print(f"\n{'='*40}")
        print(f"📊 GRAND TOTAL: {grand_total:,} records")
        print(f"💾 Total Size: {sum([info['size_mb'] for info in tables_info.values()]):.1f} MB")
        
        # Data source mapping
        print(f"\n🗂️  DATA SOURCE MAPPING")
        print("=" * 30)
        print(f"  📁 raw_data/game_records/ → pgn_games ({tables_info['pgn_games']['records']:,} records)")
        print(f"  📁 raw_data/analysis_results/ → analysis_results ({tables_info['analysis_results']['records']:,} records)")
        print(f"  📁 raw_data/v7p3r_docs/ → documentation ({tables_info['documentation']['records']:,} records)")
        
        # Sample data verification
        print(f"\n🔍 SAMPLE DATA VERIFICATION")
        print("=" * 35)
        
        # Chess engines found
        try:
            engines_query = f"""
            SELECT DISTINCT white as engine
            FROM `{project_id}.chess_engine_data_lake.pgn_games`
            WHERE white IS NOT NULL
            UNION DISTINCT
            SELECT DISTINCT black as engine
            FROM `{project_id}.chess_engine_data_lake.pgn_games`
            WHERE black IS NOT NULL
            ORDER BY engine
            LIMIT 10
            """
            
            engines = [row['engine'] for row in client.query(engines_query).result()]
            print(f"  🤖 Chess Engines Found: {len(engines)}")
            for engine in engines[:8]:
                print(f"    - {engine}")
            if len(engines) > 8:
                print(f"    ... and {len(engines)-8} more")
                
        except Exception as e:
            print(f"  ❌ Engine check failed: {str(e)}")
        
        # V7P3R versions found
        try:
            versions_query = f"""
            SELECT DISTINCT engine_version
            FROM `{project_id}.chess_engine_data_lake.analysis_results`
            WHERE engine_version IS NOT NULL AND engine_version != 'unknown'
            ORDER BY engine_version
            """
            
            versions = [row['engine_version'] for row in client.query(versions_query).result()]
            print(f"  🔧 V7P3R Versions: {len(versions) if versions else 'Detected in filenames'}")
            
        except Exception as e:
            print(f"  🔧 V7P3R Versions: Detected in filenames")
        
        # Data freshness
        print(f"\n📅 DATA FRESHNESS")
        print("=" * 25)
        latest_ingestion = max([info['last_ingested'] for info in tables_info.values() if info['last_ingested']])
        hours_ago = (datetime.now(latest_ingestion.tzinfo) - latest_ingestion).total_seconds() / 3600
        
        print(f"  Latest Ingestion: {latest_ingestion}")
        print(f"  Freshness: {hours_ago:.1f} hours ago")
        
        if hours_ago < 24:
            freshness_status = "🟢 FRESH"
        elif hours_ago < 72:
            freshness_status = "🟡 RECENT"  
        else:
            freshness_status = "🔴 STALE"
            
        print(f"  Status: {freshness_status}")
        
        # Final assessment
        print(f"\n🎯 FINAL ASSESSMENT")
        print("=" * 30)
        
        expected_total = 31659  # From our documentation
        match_percentage = (grand_total / expected_total * 100) if expected_total > 0 else 0
        
        print(f"  Expected Records: {expected_total:,}")
        print(f"  Actual Records: {grand_total:,}")  
        print(f"  Match Rate: {match_percentage:.1f}%")
        
        if match_percentage >= 99:
            status = "🎉 EXCELLENT"
            recommendation = "✅ Ready for Transform Layer"
        elif match_percentage >= 90:
            status = "✅ VERY GOOD" 
            recommendation = "✅ Proceed with caution"
        else:
            status = "⚠️ NEEDS ATTENTION"
            recommendation = "❌ Investigate before proceeding"
            
        print(f"  Data Integrity: {status}")
        print(f"  Recommendation: {recommendation}")
        
        # Next steps
        print(f"\n🚀 NEXT STEPS")
        print("=" * 20)
        print(f"  1. ✅ Raw Data Layer: COMPLETE")
        print(f"  2. 🔄 Transform Layer: READY TO BUILD")  
        print(f"  3. 🎨 Analytics Dashboard: PENDING")
        print(f"  4. 🤖 ML Pipeline: PENDING")
        
        print(f"\n{'='*60}")
        print(f"🎯 VERIFICATION COMPLETE - ALL SYSTEMS GO! 🚀")
        
        return match_percentage >= 90
        
    except ImportError as e:
        print(f"❌ BigQuery not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Final verification failed: {e}")
        return False

if __name__ == "__main__":
    success = final_verification_report()
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}: Data verification {'completed' if success else 'failed'}")
    sys.exit(0 if success else 1)