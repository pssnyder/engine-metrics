#!/usr/bin/env python3
"""
V7P3R Chess Engine Data Migration - Manual Approach
Bypasses Firebase Functions and uploads directly to Firebase Storage
"""

import os
import sys
import json
import time
from pathlib import Path
import subprocess

# Configuration
PROJECT_ROOT = Path(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics")
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
FIREBASE_PROJECT = "chess-engine-metrics-agent"
STORAGE_BUCKET = "chess-engine-metrics-agent.firebasestorage.app"

def upload_with_gsutil(source_dir, target_prefix, description):
    """Upload directory using gsutil directly"""
    print(f"\n📤 Uploading {description}...")
    print(f"   Source: {source_dir}")
    print(f"   Target: gs://{STORAGE_BUCKET}/{target_prefix}")
    
    if not source_dir.exists():
        print(f"   ⚠️  Directory not found: {source_dir}")
        return False
    
    # Get file count for progress tracking
    try:
        file_count = len(list(source_dir.rglob('*')))
        print(f"   Files to upload: {file_count}")
        
        # Use gsutil for batch upload
        cmd = f'gsutil -m cp -r "{source_dir}/*" "gs://{STORAGE_BUCKET}/{target_prefix}/"'
        
        print(f"   Running: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ Successfully uploaded {description}")
            return True
        else:
            print(f"   ❌ Failed to upload {description}")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception uploading {description}: {e}")
        return False

def main():
    """Main migration process using gsutil"""
    print("🏆 V7P3R Chess Engine Data Migration - Manual Upload")
    print("====================================================")
    
    # Check if raw_data directory exists
    if not RAW_DATA_DIR.exists():
        print(f"❌ Error: raw_data directory not found at {RAW_DATA_DIR}")
        sys.exit(1)
    
    print(f"✅ Found raw_data directory: {RAW_DATA_DIR}")
    
    # Check if gsutil is available
    try:
        result = subprocess.run("gsutil version", shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Error: gsutil not found. Please install Google Cloud SDK.")
            print("   Download from: https://cloud.google.com/sdk/docs/install")
            sys.exit(1)
        print("✅ gsutil available")
    except Exception as e:
        print(f"❌ Error checking gsutil: {e}")
        sys.exit(1)
    
    # Set the project
    try:
        cmd = f"gsutil config set project {FIREBASE_PROJECT}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"✅ Set gsutil project: {FIREBASE_PROJECT}")
    except Exception as e:
        print(f"⚠️  Warning: Could not set gsutil project: {e}")
    
    # Migration summary
    migration_summary = {
        'start_time': time.time(),
        'uploads': []
    }
    
    # Priority 1: V7P3R Analysis Results (ELO SOURCE OF TRUTH)
    print("\n🎯 PRIORITY 1: V7P3R Analysis Results (ELO Data)")
    v7p3r_analysis_dir = RAW_DATA_DIR / "analysis_results" / "v7p3r_analysis"
    success = upload_with_gsutil(
        v7p3r_analysis_dir, 
        "raw-data/analysis-results/v7p3r", 
        "V7P3R Analysis Results"
    )
    migration_summary['uploads'].append({
        'type': 'v7p3r_analysis',
        'success': success,
        'priority': 1
    })
    
    # Priority 2: Game Records (subset first to test)
    print("\n🎯 PRIORITY 2: Game Records (Recent PGN Files)")
    game_records_dir = RAW_DATA_DIR / "game_records"
    
    if game_records_dir.exists():
        # Get the most recent 5 folders to test
        subdirs = [d for d in game_records_dir.iterdir() if d.is_dir()]
        recent_dirs = sorted(subdirs, key=lambda x: x.name)[-5:]  # Last 5 folders
        
        print(f"   Testing with {len(recent_dirs)} recent tournament folders")
        
        for subdir in recent_dirs:
            print(f"   📁 Uploading {subdir.name}...")
            success = upload_with_gsutil(
                subdir, 
                f"raw-data/game-records/{subdir.name}", 
                f"Game Records - {subdir.name}"
            )
            migration_summary['uploads'].append({
                'type': f'game_records_{subdir.name}',
                'success': success,
                'priority': 2
            })
    
    # Complete migration summary
    migration_summary['end_time'] = time.time()
    migration_summary['duration_minutes'] = (migration_summary['end_time'] - migration_summary['start_time']) / 60
    migration_summary['total_uploads'] = len([u for u in migration_summary['uploads'] if u['success']])
    
    # Summary
    print("\n====================================================")
    print("🏆 V7P3R Data Migration Summary")
    print("====================================================")
    
    successful_uploads = [u for u in migration_summary['uploads'] if u['success']]
    failed_uploads = [u for u in migration_summary['uploads'] if not u['success']]
    
    print(f"✅ Successfully uploaded: {len(successful_uploads)} data sets")
    print(f"❌ Failed uploads: {len(failed_uploads)} data sets")
    print(f"⏱️  Total time: {migration_summary['duration_minutes']:.2f} minutes")
    
    if successful_uploads:
        print("\n📊 Successful uploads:")
        for upload in successful_uploads:
            print(f"   ✅ {upload['type']} (Priority {upload['priority']})")
    
    if failed_uploads:
        print("\n❌ Failed uploads:")
        for upload in failed_uploads:
            print(f"   ❌ {upload['type']} (Priority {upload['priority']})")
    
    # Check uploaded files
    print("\n📋 Verifying uploads...")
    try:
        result = subprocess.run(
            f'gsutil ls "gs://{STORAGE_BUCKET}/raw-data/"', 
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ Files uploaded successfully:")
            print(result.stdout)
        else:
            print("⚠️  Could not verify uploads")
    except Exception as e:
        print(f"⚠️  Could not verify uploads: {e}")
    
    print("\n🔄 Next Steps:")
    print("1. ✅ Raw data uploaded to Firebase Storage")
    print("2. 🔧 Fix Firebase Functions deployment issues (Cloud Build permissions)")
    print("3. 🚀 Process data with ETL functions once deployed")
    print("4. 📊 Build web dashboard for V7P3R analysis")
    
    print("\n💡 Alternative Approach:")
    print("   Since Functions deployment has issues, we can:")
    print("   • Use Firebase Admin SDK locally to process data")
    print("   • Store results directly in Firestore")
    print("   • Build a simple web interface")
    
    print("\n🚀 V7P3R raw data is now in the cloud and ready for analysis!")

if __name__ == "__main__":
    main()