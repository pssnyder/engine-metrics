#!/usr/bin/env python3
"""
Schema Explorer - Check what fields actually exist in our tables
"""

import os
import sys

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def explore_schemas():
    """Explore actual table schemas"""
    
    try:
        from google.cloud import bigquery
        
        project_id = 'chess-engine-metrics-agent'
        client = bigquery.Client(project=project_id)
        
        print("🔍 Schema Explorer")
        print("=" * 50)
        
        tables = ['pgn_games', 'analysis_results', 'documentation']
        
        for table_name in tables:
            print(f"\n📋 {table_name.upper()} TABLE SCHEMA:")
            try:
                table_ref = f"{project_id}.chess_engine_data_lake.{table_name}"
                table = client.get_table(table_ref)
                
                print(f"  Total fields: {len(table.schema)}")
                print(f"  Fields:")
                
                for field in table.schema:
                    print(f"    - {field.name:<20} : {field.field_type:<10} ({field.mode})")
                
                # Show sample data
                print(f"\n  Sample record:")
                sample_query = f"SELECT * FROM `{table_ref}` LIMIT 1"
                sample = list(client.query(sample_query).result())
                
                if sample:
                    record = dict(sample[0])
                    for key, value in list(record.items())[:8]:  # Show first 8 fields
                        value_str = str(value)[:50] if value else "NULL"
                        print(f"    {key:<20} : {value_str}")
                    if len(record) > 8:
                        print(f"    ... and {len(record)-8} more fields")
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ BigQuery not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Schema exploration failed: {e}")
        return False

if __name__ == "__main__":
    success = explore_schemas()
    sys.exit(0 if success else 1)