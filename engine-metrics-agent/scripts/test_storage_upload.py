#!/usr/bin/env python3
"""
V7P3R Chess Engine Data Migration - Test Upload
Test upload of a small sample to verify Firebase Storage connectivity
"""

import os
import sys
import subprocess
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics")
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
FIREBASE_PROJECT = "chess-engine-metrics-agent"
STORAGE_BUCKET = "chess-engine-metrics-agent.firebasestorage.app"

def test_storage_access():
    """Test Firebase Storage bucket access"""
    print("🔍 Testing Firebase Storage Access...")
    
    try:
        # List bucket contents
        cmd = f'gsutil ls "gs://{STORAGE_BUCKET}/"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Successfully accessed Firebase Storage bucket")
            print("   Current contents:")
            if result.stdout.strip():
                print(f"   {result.stdout}")
            else:
                print("   (bucket is empty)")
            return True
        else:
            print(f"❌ Failed to access Firebase Storage bucket")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Exception testing storage access: {e}")
        return False

def find_sample_files():
    """Find small sample files for testing"""
    print("\n🔍 Looking for sample files to test upload...")
    
    sample_files = []
    
    # Look for small files in various directories
    if RAW_DATA_DIR.exists():
        # Check for small analysis files
        analysis_dir = RAW_DATA_DIR / "analysis_results" / "v7p3r_analysis"
        if analysis_dir.exists():
            for file in analysis_dir.glob("*.json"):
                size = file.stat().st_size
                if size < 1024 * 1024:  # Less than 1MB
                    sample_files.append(('analysis', file, size))
                    break
        
        # Check for small game files
        game_dir = RAW_DATA_DIR / "game_records"
        if game_dir.exists():
            for subdir in game_dir.iterdir():
                if subdir.is_dir():
                    for file in subdir.glob("*.pgn"):
                        size = file.stat().st_size
                        if size < 1024 * 1024:  # Less than 1MB
                            sample_files.append(('game', file, size))
                            if len(sample_files) >= 2:
                                break
                    if len(sample_files) >= 2:
                        break
    
    return sample_files

def upload_sample_file(file_type, file_path, file_size):
    """Upload a single sample file"""
    print(f"\n📤 Uploading sample {file_type} file...")
    print(f"   File: {file_path.name}")
    print(f"   Size: {file_size:,} bytes")
    
    try:
        # Determine target path based on file type
        if file_type == 'analysis':
            target_path = f"raw-data/analysis-results/v7p3r/test-{file_path.name}"
        elif file_type == 'game':
            target_path = f"raw-data/game-records/test/{file_path.name}"
        else:
            target_path = f"raw-data/test/{file_path.name}"
        
        # Upload file
        cmd = f'gsutil cp "{file_path}" "gs://{STORAGE_BUCKET}/{target_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ Successfully uploaded to {target_path}")
            return True
        else:
            print(f"   ❌ Failed to upload")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception uploading file: {e}")
        return False

def main():
    """Main test process"""
    print("🏆 V7P3R Chess Engine Data Migration - Storage Test")
    print("==================================================")
    
    # Test 1: Check storage access
    if not test_storage_access():
        print("\n❌ Cannot access Firebase Storage. Please check:")
        print("   1. Firebase authentication: firebase login")
        print("   2. Project permissions")
        print("   3. Storage bucket exists")
        sys.exit(1)
    
    # Test 2: Find sample files
    sample_files = find_sample_files()
    
    if not sample_files:
        print("❌ No small sample files found for testing")
        print(f"   Please check that raw data exists in: {RAW_DATA_DIR}")
        sys.exit(1)
    
    print(f"✅ Found {len(sample_files)} sample files for testing")
    
    # Test 3: Upload samples
    success_count = 0
    for file_type, file_path, file_size in sample_files:
        if upload_sample_file(file_type, file_path, file_size):
            success_count += 1
    
    # Test 4: Verify uploads
    print(f"\n📋 Verifying uploads...")
    try:
        result = subprocess.run(
            f'gsutil ls -r "gs://{STORAGE_BUCKET}/raw-data/"', 
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ Files in storage:")
            print(result.stdout)
        else:
            print("⚠️  Could not list uploaded files")
    except Exception as e:
        print(f"⚠️  Could not verify uploads: {e}")
    
    # Summary
    print("\n==================================================")
    print("🏆 Storage Test Summary")
    print("==================================================")
    
    print(f"✅ Successfully uploaded: {success_count}/{len(sample_files)} files")
    
    if success_count == len(sample_files):
        print("\n🎉 EXCELLENT! Firebase Storage is working perfectly!")
        print("\n🔄 Next Steps:")
        print("1. ✅ Storage access confirmed")
        print("2. 🚀 Run full data migration")
        print("3. 🔧 Process data (locally if Functions have issues)")
        print("4. 📊 Build V7P3R analysis dashboard")
        
        print("\n💡 Ready to proceed with:")
        print("   python scripts/upload_v7p3r_data_manual.py")
    else:
        print("\n⚠️  Some uploads failed. Please check:")
        print("   • Firebase project permissions")
        print("   • Storage bucket configuration")
        print("   • File paths and permissions")
    
    print("\n🚀 Storage connectivity test complete!")

if __name__ == "__main__":
    main()