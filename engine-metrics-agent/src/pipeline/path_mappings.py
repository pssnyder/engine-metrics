#!/usr/bin/env python3
"""
Path mapping configuration for Move Layer
Maps local raw_data structure to Firebase Storage bucket structure
"""

# Path mappings from local raw_data structure to bucket structure
PATH_MAPPINGS = {
    # Local raw_data subdirectories -> Bucket top-level directories (1:1 mapping)
    "analysis_results/": "analysis_results/",
    "game_records/": "game_records/",
    "v7p3r_docs/": "v7p3r_docs/",
}

def get_bucket_path(local_relative_path):
    """
    Convert local raw_data relative path to bucket path
    
    Args:
        local_relative_path: Path relative to raw_data directory
        
    Returns:
        Path to use in bucket (without gs:// prefix)
    """
    # Normalize path separators
    local_path = local_relative_path.replace('\\', '/')
    
    # Check for exact mappings
    for local_prefix, bucket_prefix in PATH_MAPPINGS.items():
        if local_path.startswith(local_prefix):
            return local_path.replace(local_prefix, bucket_prefix, 1)
    
    # Default: keep the same structure
    return local_path

def get_local_path(bucket_path):
    """
    Convert bucket path to local raw_data relative path
    
    Args:
        bucket_path: Path in bucket (without gs:// prefix)
        
    Returns:
        Path relative to raw_data directory
    """
    # Normalize path separators  
    bucket_path = bucket_path.replace('\\', '/')
    
    # Check for reverse mappings
    for local_prefix, bucket_prefix in PATH_MAPPINGS.items():
        if bucket_path.startswith(bucket_prefix):
            return bucket_path.replace(bucket_prefix, local_prefix, 1)
    
    # Default: keep the same structure
    return bucket_path

# Example usage and testing
if __name__ == "__main__":
    test_cases = [
        "analysis_results/v7p3r/some_analysis.json",
        "game_records/Engine Battle 20250920/battle.pgn", 
        "v7p3r_docs/development_plan.md",
        "some_other_file.txt"
    ]
    
    print("Path Mapping Test Cases:")
    print("=" * 50)
    
    for test_path in test_cases:
        bucket_path = get_bucket_path(test_path)
        back_to_local = get_local_path(bucket_path)
        
        print(f"Local:  {test_path}")
        print(f"Bucket: {bucket_path}")
        print(f"Back:   {back_to_local}")
        print(f"Match:  {'✓' if back_to_local == test_path else '✗'}")
        print()