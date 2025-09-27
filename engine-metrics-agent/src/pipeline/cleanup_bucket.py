#!/usr/bin/env python3
"""
Bucket Cleanup Script - Chess Engine Metrics
Reorganizes Firebase Storage bucket to remove duplicates and standardize structure
"""

import subprocess
import json
import sys
from pathlib import Path

BUCKET_NAME = "chess-engine-metrics-agent.firebasestorage.app"
TEMP_PREFIX = "_cleanup_temp"

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

def list_bucket_contents():
    """List all objects in the bucket"""
    print("Analyzing bucket contents...")
    output = run_gsutil(f"ls -r gs://{BUCKET_NAME}")
    if output:
        objects = [line.strip() for line in output.split('\n') if line.strip() and not line.endswith(':')]
    else:
        objects = []
    return objects

def identify_duplicates(objects):
    """Identify duplicate files between old structure and raw-data/ nested structure"""
    duplicates = []
    nested_files = [obj for obj in objects if '/raw-data/' in obj]
    top_level_files = [obj for obj in objects if '/raw-data/' not in obj]
    
    for nested_file in nested_files:
        # Extract the path after raw-data/
        relative_path = nested_file.split('/raw-data/', 1)[1]
        
        # Look for corresponding top-level file
        for top_file in top_level_files:
            top_relative = top_file.replace(f'gs://{BUCKET_NAME}/', '')
            
            # Check if this represents the same logical file
            if (relative_path == top_relative or 
                relative_path.replace('analysis-results/', 'analysis_results/') == top_relative or
                relative_path.replace('game-records/', 'game_results/') == top_relative):
                duplicates.append({
                    'nested': nested_file,
                    'top_level': top_file,
                    'relative_path': relative_path
                })
                break
    
    return duplicates

def cleanup_bucket():
    """Main cleanup function"""
    print(f"Starting cleanup of bucket: gs://{BUCKET_NAME}")
    
    # List current contents
    objects = list_bucket_contents()
    print(f"Found {len(objects)} objects in bucket")
    
    # Identify duplicates
    duplicates = identify_duplicates(objects)
    print(f"Found {len(duplicates)} potential duplicates")
    
    if duplicates:
        print("\nDuplicate Analysis:")
        for dup in duplicates:
            print(f"  Nested: {dup['nested']}")
            print(f"  Top Level: {dup['top_level']}")
            print(f"  Relative: {dup['relative_path']}")
            print()
    
    # Confirm with user
    if duplicates:
        response = input(f"Delete {len(duplicates)} nested duplicate files? (y/N): ")
        if response.lower() == 'y':
            print("Deleting nested duplicates...")
            for dup in duplicates:
                try:
                    run_gsutil(f"rm '{dup['nested']}'")
                    print(f"Deleted: {dup['nested']}")
                except Exception as e:
                    print(f"Failed to delete {dup['nested']}: {e}")
        else:
            print("Cleanup cancelled")
            return
    
    # Remove empty raw-data directory structure if it exists
    try:
        print("Removing empty raw-data/ directory structure...")
        run_gsutil(f"ls gs://{BUCKET_NAME}/raw-data/", check=False)
        # If the directory exists but is empty after cleanup, gsutil will handle it
        run_gsutil(f"rm -r gs://{BUCKET_NAME}/raw-data/", check=False)
    except:
        pass  # Directory might not exist or already be empty
    
    print("Cleanup completed!")
    
    # Show final structure
    print("\nFinal bucket structure:")
    final_objects = list_bucket_contents()
    
    # Group by top-level directories
    directories = {}
    for obj in final_objects:
        path_parts = obj.replace(f'gs://{BUCKET_NAME}/', '').split('/')
        if len(path_parts) > 1:
            top_dir = path_parts[0]
            directories.setdefault(top_dir, []).append(obj)
        else:
            directories.setdefault('_root', []).append(obj)
    
    for dir_name, files in directories.items():
        print(f"  {dir_name}/: {len(files)} files")

def main():
    """Main function"""
    print("Chess Engine Metrics - Bucket Cleanup Tool")
    print("=" * 50)
    
    try:
        cleanup_bucket()
    except KeyboardInterrupt:
        print("\nCleanup cancelled by user")
        return 1
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())