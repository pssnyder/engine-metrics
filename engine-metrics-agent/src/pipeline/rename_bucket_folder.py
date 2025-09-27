#!/usr/bin/env python3
"""
Rename bucket folder from game_results to game_records
to match local directory structure
"""

import subprocess
import sys

def run_gsutil(command, check=True):
    """Run gsutil command and return output"""
    cmd = f"gsutil {command}"
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Stderr: {e.stderr}")
        if check:
            raise
        return None

def main():
    bucket = "chess-engine-metrics-agent.firebasestorage.app"
    
    print("Renaming game_results/ to game_records/ in bucket...")
    print(f"Bucket: gs://{bucket}")
    
    # Confirm with user
    response = input("This will rename game_results/ to game_records/. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled")
        return 1
    
    try:
        # Copy all files from game_results/ to game_records/
        print("Step 1: Copying files to new location...")
        run_gsutil(f"cp -r gs://{bucket}/game_results/* gs://{bucket}/game_records/")
        
        # Verify the copy worked
        print("Step 2: Verifying copy...")
        old_count = run_gsutil(f"ls -r gs://{bucket}/game_results/ | wc -l")
        new_count = run_gsutil(f"ls -r gs://{bucket}/game_records/ | wc -l")
        
        print(f"Old location files: {old_count}")
        print(f"New location files: {new_count}")
        
        if old_count == new_count:
            # Delete the old directory
            print("Step 3: Removing old location...")
            run_gsutil(f"rm -r gs://{bucket}/game_results/")
            print("✅ Successfully renamed game_results/ to game_records/")
        else:
            print("❌ File counts don't match. Not removing old directory for safety.")
            return 1
            
    except Exception as e:
        print(f"❌ Error during rename: {e}")
        return 1
    
    print("✅ Folder rename completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())