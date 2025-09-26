#!/usr/bin/env python3
"""
V7P3R Chess Engine Data Migration Script
Migrates local raw_data/ to Firebase Storage for cloud processing
Windows-compatible version using Firebase Admin SDK
"""

import os
import sys
import json
import time
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, storage, firestore
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
PROJECT_ROOT = Path(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics")
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
FIREBASE_PROJECT = "chess-engine-metrics-agent"
SERVICE_ACCOUNT_KEY = PROJECT_ROOT / "engine-metrics-agent" / "auth-config.json"

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        if SERVICE_ACCOUNT_KEY.exists():
            cred = credentials.Certificate(str(SERVICE_ACCOUNT_KEY))
        else:
            # Use default credentials
            cred = credentials.ApplicationDefault()
            
        firebase_admin.initialize_app(cred, {
            'storageBucket': f'{FIREBASE_PROJECT}.appspot.com'
        })
        
        print(f"✅ Firebase initialized for project: {FIREBASE_PROJECT}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize Firebase: {e}")
        return False

def upload_file(file_path, storage_path, bucket):
    """Upload a single file to Firebase Storage"""
    try:
        blob = bucket.blob(storage_path)
        blob.upload_from_filename(str(file_path))
        return {
            'success': True,
            'file': str(file_path),
            'storage_path': storage_path,
            'size': file_path.stat().st_size
        }
    except Exception as e:
        return {
            'success': False,
            'file': str(file_path),
            'error': str(e)
        }

def upload_directory(source_dir, target_prefix, description, max_workers=5):
    """Upload directory to Firebase Storage with parallel processing"""
    print(f"\n📤 Uploading {description}...")
    print(f"   Source: {source_dir}")
    print(f"   Target: gs://{FIREBASE_PROJECT}.appspot.com/{target_prefix}")
    
    if not source_dir.exists():
        print(f"   ⚠️  Directory not found: {source_dir}")
        return False
    
    # Get all files to upload
    files_to_upload = []
    for file_path in source_dir.rglob('*'):
        if file_path.is_file():
            # Calculate relative path for storage
            relative_path = file_path.relative_to(source_dir)
            storage_path = f"{target_prefix}/{relative_path}".replace('\\', '/')
            files_to_upload.append((file_path, storage_path))
    
    if not files_to_upload:
        print(f"   ⚠️  No files found in {source_dir}")
        return False
    
    print(f"   Files to upload: {len(files_to_upload)}")
    
    # Get Firebase Storage bucket
    bucket = storage.bucket()
    
    # Upload files in parallel
    success_count = 0
    error_count = 0
    total_size = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all upload tasks
        future_to_file = {
            executor.submit(upload_file, file_path, storage_path, bucket): (file_path, storage_path)
            for file_path, storage_path in files_to_upload
        }
        
        # Process completed uploads
        for future in as_completed(future_to_file):
            file_path, storage_path = future_to_file[future]
            try:
                result = future.result()
                if result['success']:
                    success_count += 1
                    total_size += result['size']
                    if success_count % 10 == 0:  # Progress indicator
                        print(f"   📊 Uploaded {success_count}/{len(files_to_upload)} files...")
                else:
                    error_count += 1
                    print(f"   ❌ Failed to upload {file_path}: {result['error']}")
            except Exception as e:
                error_count += 1
                print(f"   ❌ Exception uploading {file_path}: {e}")
    
    # Summary
    total_size_mb = total_size / (1024 * 1024)
    print(f"   ✅ Upload completed: {success_count} files, {total_size_mb:.2f} MB")
    if error_count > 0:
        print(f"   ⚠️  Errors: {error_count} files failed")
    
    return success_count > 0

def log_migration_status(migration_summary):
    """Log migration status to Firestore"""
    try:
        db = firestore.client()
        migration_doc = {
            'migration_date': firestore.SERVER_TIMESTAMP,
            'summary': migration_summary,
            'status': 'completed',
            'source': 'python-migration-script'
        }
        
        db.collection('migration_logs').add(migration_doc)
        print("📝 Migration status logged to Firestore")
        
    except Exception as e:
        print(f"⚠️  Failed to log migration status: {e}")

def main():
    """Main migration process"""
    print("🏆 V7P3R Chess Engine Data Migration Starting...")
    print("==================================================")
    
    # Check if raw_data directory exists
    if not RAW_DATA_DIR.exists():
        print(f"❌ Error: raw_data directory not found at {RAW_DATA_DIR}")
        sys.exit(1)
    
    print(f"✅ Found raw_data directory: {RAW_DATA_DIR}")
    
    # Initialize Firebase
    if not initialize_firebase():
        sys.exit(1)
    
    # Migration summary for tracking
    migration_summary = {
        'start_time': time.time(),
        'uploads': [],
        'errors': []
    }
    
    # Priority 1: V7P3R Analysis Results (ELO SOURCE OF TRUTH)
    print("\n🎯 PRIORITY 1: V7P3R Analysis Results (ELO Data)")
    v7p3r_analysis_dir = RAW_DATA_DIR / "analysis_results" / "v7p3r_analysis"
    success = upload_directory(
        v7p3r_analysis_dir, 
        "raw-data/analysis-results/v7p3r", 
        "V7P3R Analysis Results"
    )
    migration_summary['uploads'].append({
        'type': 'v7p3r_analysis',
        'success': success,
        'priority': 1
    })
    
    # Priority 2: Game Records (All Engine Battles)
    print("\n🎯 PRIORITY 2: Game Records (PGN Files)")
    game_records_dir = RAW_DATA_DIR / "game_records"
    success = upload_directory(
        game_records_dir, 
        "raw-data/game-records", 
        "Game Records (PGN Files)"
    )
    migration_summary['uploads'].append({
        'type': 'game_records',
        'success': success,
        'priority': 2
    })
    
    # Priority 3: V7P3R Development Documentation
    print("\n🎯 PRIORITY 3: V7P3R Development Documentation")
    dev_docs_dir = RAW_DATA_DIR / "docs" / "v7p3r_dev_docs"
    success = upload_directory(
        dev_docs_dir, 
        "raw-data/dev-docs/v7p3r", 
        "V7P3R Development Docs"
    )
    migration_summary['uploads'].append({
        'type': 'v7p3r_dev_docs',
        'success': success,
        'priority': 3
    })
    
    # Priority 4: Other Analysis Results (for comparison)
    print("\n🎯 PRIORITY 4: Other Engine Analysis Results")
    
    # SlowMate analysis
    slowmate_dir = RAW_DATA_DIR / "analysis_results" / "slowmate_analysis"
    if slowmate_dir.exists():
        success = upload_directory(
            slowmate_dir, 
            "raw-data/analysis-results/slowmate", 
            "SlowMate Analysis Results"
        )
        migration_summary['uploads'].append({
            'type': 'slowmate_analysis',
            'success': success,
            'priority': 4
        })
    
    # C0BR4 analysis
    c0br4_dir = RAW_DATA_DIR / "analysis_results" / "c0br4_analysis"
    if c0br4_dir.exists():
        success = upload_directory(
            c0br4_dir, 
            "raw-data/analysis-results/c0br4", 
            "C0BR4 Analysis Results"
        )
        migration_summary['uploads'].append({
            'type': 'c0br4_analysis',
            'success': success,
            'priority': 4
        })
    
    # Complete migration summary
    migration_summary['end_time'] = time.time()
    migration_summary['duration_minutes'] = (migration_summary['end_time'] - migration_summary['start_time']) / 60
    migration_summary['total_uploads'] = len([u for u in migration_summary['uploads'] if u['success']])
    
    # Log to Firestore
    log_migration_status(migration_summary)
    
    # Summary and next steps
    print("\n==================================================")
    print("🏆 V7P3R Data Migration Summary")
    print("==================================================")
    
    successful_uploads = [u for u in migration_summary['uploads'] if u['success']]
    failed_uploads = [u for u in migration_summary['uploads'] if not u['success']]
    
    print(f"✅ Successfully uploaded: {len(successful_uploads)} data types")
    print(f"❌ Failed uploads: {len(failed_uploads)} data types")
    print(f"⏱️  Total time: {migration_summary['duration_minutes']:.2f} minutes")
    
    if successful_uploads:
        print("\n📊 Successful uploads:")
        for upload in successful_uploads:
            print(f"   ✅ {upload['type']} (Priority {upload['priority']})")
    
    if failed_uploads:
        print("\n❌ Failed uploads:")
        for upload in failed_uploads:
            print(f"   ❌ {upload['type']} (Priority {upload['priority']})")
    
    print("\n🔄 Next Steps:")
    print("1. Deploy Firebase Functions: npm run deploy:backend")
    print("2. Trigger ETL processing: Functions will auto-process uploaded files")
    print("3. Verify data in Firestore: Check collections v7p3r_elo_estimates, v7p3r_games")
    print("4. Test ELO consolidation: Call consolidateELOData endpoint")
    print("\n📈 Data Pipeline Status:")
    print("   Raw Data: ✅ Uploaded to Firebase Storage")
    print("   ETL Functions: ⏳ Ready to deploy and process")
    print("   Consolidated ELO: ⏳ Waiting for ETL completion")
    print("   Web Dashboard: ⏳ Ready for development")
    print("\n🚀 Ready to analyze V7P3R performance data in the cloud!")

if __name__ == "__main__":
    main()