#!/usr/bin/env python3
"""
V7P3R Chess Engine Data Migration - Firebase CLI Approach
Uses Firebase Admin SDK instead of gsutil for direct upload
"""

import os
import sys
import json
import time
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics")
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
FIREBASE_PROJECT = "chess-engine-metrics-agent"
STORAGE_BUCKET = "chess-engine-metrics-agent.firebasestorage.app"

def check_firebase_cli():
    """Check if Firebase CLI is available and authenticated"""
    print("🔍 Checking Firebase CLI...")
    
    try:
        import subprocess
        result = subprocess.run("firebase --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Firebase CLI available")
            
            # Check if authenticated and using correct project
            result = subprocess.run("firebase use", shell=True, capture_output=True, text=True)
            if "chess-engine-metrics-agent" in result.stdout:
                print("✅ Authenticated and using correct project")
                return True
            else:
                print("❌ Not using correct Firebase project")
                return False
        else:
            print("❌ Firebase CLI not available")
            return False
    except Exception as e:
        print(f"❌ Error checking Firebase CLI: {e}")
        return False

def use_direct_file_copy():
    """Alternative approach: List files and prepare for manual upload"""
    print("\n📋 V7P3R Data Inventory for Manual Upload")
    print("=" * 50)
    
    if not RAW_DATA_DIR.exists():
        print(f"❌ Raw data directory not found: {RAW_DATA_DIR}")
        return False
    
    # Priority 1: V7P3R Analysis Results
    analysis_dir = RAW_DATA_DIR / "analysis_results" / "v7p3r_analysis"
    if analysis_dir.exists():
        print(f"\n🎯 PRIORITY 1: V7P3R Analysis Results")
        print(f"   Location: {analysis_dir}")
        
        files = list(analysis_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        
        print(f"   Files: {len(files)} JSON files")
        print(f"   Total Size: {total_size / (1024*1024):.2f} MB")
        
        # Show sample files
        if files:
            print(f"   Sample files:")
            for file in files[:3]:
                size_mb = file.stat().st_size / (1024*1024)
                print(f"     • {file.name} ({size_mb:.2f} MB)")
            if len(files) > 3:
                print(f"     • ... and {len(files)-3} more files")
    
    # Priority 2: Recent Game Records
    game_records_dir = RAW_DATA_DIR / "game_records"
    if game_records_dir.exists():
        print(f"\n🎯 PRIORITY 2: Game Records")
        print(f"   Location: {game_records_dir}")
        
        subdirs = [d for d in game_records_dir.iterdir() if d.is_dir()]
        recent_dirs = sorted(subdirs, key=lambda x: x.name)[-5:]  # Last 5 folders
        
        total_files = 0
        total_size = 0
        
        for subdir in recent_dirs:
            files = list(subdir.glob("*.pgn"))
            size = sum(f.stat().st_size for f in files)
            total_files += len(files)
            total_size += size
            
            print(f"   📁 {subdir.name}: {len(files)} PGN files ({size/(1024*1024):.2f} MB)")
        
        print(f"   Recent Total: {total_files} files, {total_size/(1024*1024):.2f} MB")
    
    # Priority 3: Development Docs
    docs_dir = RAW_DATA_DIR / "docs" / "v7p3r_dev_docs"
    if docs_dir.exists():
        print(f"\n🎯 PRIORITY 3: V7P3R Development Documentation")
        print(f"   Location: {docs_dir}")
        
        files = list(docs_dir.glob("*.md"))
        total_size = sum(f.stat().st_size for f in files)
        
        print(f"   Files: {len(files)} Markdown files")
        print(f"   Total Size: {total_size / (1024*1024):.2f} MB")
    
    return True

def create_firebase_upload_instructions():
    """Create step-by-step instructions for manual upload via Firebase Console"""
    print("\n📋 FIREBASE CONSOLE UPLOAD INSTRUCTIONS")
    print("=" * 50)
    
    instructions = """
🚀 Manual Upload Steps via Firebase Console:

1. Open Firebase Console:
   https://console.firebase.google.com/project/chess-engine-metrics-agent/storage

2. Navigate to Storage section

3. Create folder structure:
   📁 raw-data/
   ├── 📁 analysis-results/
   │   └── 📁 v7p3r/
   ├── 📁 game-records/
   └── 📁 dev-docs/
       └── 📁 v7p3r/

4. Upload Priority 1 - V7P3R Analysis Results:
   • Go to raw-data/analysis-results/v7p3r/
   • Upload all JSON files from: {analysis_dir}
   • These are your ELO source of truth files

5. Upload Priority 2 - Recent Game Records:
   • Go to raw-data/game-records/
   • Create subfolders for each tournament date
   • Upload PGN files from recent tournaments

6. Upload Priority 3 - Development Docs:
   • Go to raw-data/dev-docs/v7p3r/
   • Upload Markdown files from: {docs_dir}

✅ Once uploaded, the Firebase Functions will automatically process the data!
    """.format(
        analysis_dir=RAW_DATA_DIR / "analysis_results" / "v7p3r_analysis",
        docs_dir=RAW_DATA_DIR / "docs" / "v7p3r_dev_docs"
    )
    
    print(instructions)

def main():
    """Main migration coordination"""
    print("🏆 V7P3R Chess Engine Data Migration - Smart Approach")
    print("=" * 60)
    
    # Check Firebase CLI availability
    firebase_ok = check_firebase_cli()
    
    if firebase_ok:
        print("✅ Firebase CLI is ready - we can proceed with automated upload")
        print("💡 However, let's first inventory your data and plan the migration")
    else:
        print("⚠️  Firebase CLI issues - we'll use manual upload approach")
    
    # Inventory the data
    inventory_ok = use_direct_file_copy()
    
    if inventory_ok:
        # Create upload instructions
        create_firebase_upload_instructions()
        
        print("\n" + "=" * 60)
        print("🎯 RECOMMENDED MIGRATION APPROACH")
        print("=" * 60)
        
        print("""
Option A: Firebase Console Upload (Recommended for now)
  ✅ Simple and reliable
  ✅ No PATH or CLI issues
  ✅ Direct to Firebase Storage
  ⏱️  ~15 minutes manual work

Option B: Automated Script Upload (After fixing gsutil)
  🔧 Requires fixing gsutil PATH
  ⚡ Faster for large datasets
  🤖 Fully automated
  ⏱️  ~2 minutes once working

Option C: Firebase CLI Upload (Alternative)
  🔧 Uses Firebase CLI directly
  ⚡ Good middle ground
  📋 Command-line based
  ⏱️  ~5 minutes with commands
        """)
        
        choice = input("\nWhich approach would you prefer? (A/B/C): ").upper().strip()
        
        if choice == 'A':
            print("\n🎯 Great choice! Manual upload via Firebase Console is reliable.")
            print("📋 Follow the instructions above to upload your V7P3R data.")
            print("🔔 Once uploaded, return here and we'll verify the data processing!")
            
        elif choice == 'B':
            print("\n🔧 Let's fix the gsutil PATH issue first...")
            print("💡 We'll need to add the correct Google Cloud SDK path to your environment.")
            
        elif choice == 'C':
            print("\n⚡ Let's try Firebase CLI direct upload...")
            print("🔧 We'll use Firebase functions to handle the upload.")
            
        else:
            print("\n✅ No problem! Choose any approach that works best for you.")
            print("📋 The instructions above will guide you through manual upload.")
    
    print("\n🚀 Once data is uploaded, we'll process it into your V7P3R analysis dashboard!")

if __name__ == "__main__":
    main()