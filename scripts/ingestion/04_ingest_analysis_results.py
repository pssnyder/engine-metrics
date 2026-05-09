#!/usr/bin/env python3
"""
Analysis Results Ingestion Script
Extracts diverse analysis JSON files from GCS to BigQuery

Handles multiple analysis types:
- perft (performance test)
- puzzle (tactical puzzle analysis)
- tactical (tactical sequence analysis)
- performance (speed/memory profiling)
- regression (regression testing)
- comparison (engine vs engine)
- validation (correctness validation)
- heuristics (heuristic evaluation)
- memory (memory profiling)
- weakness (weakness identification)

Usage:
    python 04_ingest_analysis_results.py [--dry-run] [--limit N]
"""

import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from google.cloud import bigquery, storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "chess-engine-metrics-agent"
DATASET_ID = "conformed_layer"
TARGET_TABLE = "analysis_results"
BUCKET_NAME = "v7p3r-raw-data"
SOURCE_PREFIX = "analysis_results/"


def generate_analysis_id(file_path: str) -> str:
    """
    Generate unique analysis ID from file path.
    
    Args:
        file_path: GCS file path
        
    Returns:
        SHA256 hash (first 16 chars) as analysis ID
    """
    return hashlib.sha256(file_path.encode()).hexdigest()[:16]


def classify_analysis_type(file_name: str) -> str:
    """
    Classify analysis type from filename.
    
    Args:
        file_name: Name of analysis file
        
    Returns:
        Analysis type category
    """
    name_lower = file_name.lower()
    
    if 'perft' in name_lower:
        return 'perft'
    elif 'puzzle' in name_lower or 'sequence_analysis' in name_lower:
        return 'puzzle'
    elif 'tactical' in name_lower:
        return 'tactical'
    elif 'performance' in name_lower or 'profile' in name_lower or 'profiling' in name_lower:
        return 'performance'
    elif 'regression' in name_lower:
        return 'regression'
    elif 'comparison' in name_lower or 'vs_' in name_lower or '_vs_' in name_lower or 'gauntlet' in name_lower:
        return 'comparison'
    elif 'validation' in name_lower or 'verify' in name_lower or 'verification' in name_lower or 'acceptance' in name_lower:
        return 'validation'
    elif 'heuristic' in name_lower:
        return 'heuristics'
    elif 'memory' in name_lower:
        return 'memory'
    elif 'weakness' in name_lower or 'diagnostic' in name_lower:
        return 'weakness'
    else:
        return 'other'


def extract_engine_version(file_name: str, content: Dict[str, Any]) -> Optional[str]:
    """
    Extract engine version from filename or content.
    
    Args:
        file_name: Name of analysis file
        content: Parsed JSON content
        
    Returns:
        Engine version string or None
    """
    # Try content first (but clean it up if it has V7P3R prefix)
    if 'engine_version' in content:
        version = content['engine_version']
        # Clean up "V7P3R_v10.2" to just "v10.2"
        match = re.search(r'v(\d+)\.(\d+)', version)
        if match:
            return f"v{match.group(1)}.{match.group(2)}"
        return version
    
    # Try filename patterns
    # Pattern: V7P3R_v10_2_... or v18_3_... or v18.3...
    version_patterns = [
        r'V7P3R_v(\d+)_(\d+)',  # V7P3R_v10_2
        r'V7P3R_v(\d+)\.(\d+)',  # V7P3R_v10.2
        r'v(\d+)_(\d+)_',        # v18_3_
        r'v(\d+)\.(\d+)',        # v18.3
    ]
    
    for pattern in version_patterns:
        match = re.search(pattern, file_name)
        if match:
            major = match.group(1)
            minor = match.group(2)
            return f"v{major}.{minor}"
    
    return None


def extract_opponent_engine(file_name: str, content: Dict[str, Any]) -> Optional[str]:
    """
    Extract opponent engine name from comparison analysis.
    
    Args:
        file_name: Name of analysis file
        content: Parsed JSON content
        
    Returns:
        Opponent engine name or None
    """
    name_lower = file_name.lower()
    
    if 'stockfish' in name_lower:
        return 'Stockfish'
    elif 'alpha' in name_lower:
        return 'V7P3R Alpha'
    elif 'beta' in name_lower:
        return 'V7P3R Beta'
    
    # Check content for opponent info
    if 'opponent' in content:
        return content['opponent']
    
    return None


def extract_perft_metrics(content: Dict[str, Any]) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[float], Optional[int]]:
    """
    Extract metrics from perft analysis.
    
    Returns:
        (total_tests, passed_tests, failed_tests, avg_time, avg_nps)
    """
    summary = content.get('summary', {})
    
    total = summary.get('total_tests')
    passed = summary.get('passed_tests')
    failed = summary.get('failed_tests')
    
    perf_summary = summary.get('performance_summary', {})
    avg_nps = perf_summary.get('avg_nps')
    
    # Calculate average time if positions exist
    avg_time = None
    positions = content.get('positions', {})
    if positions:
        times = []
        # Handle both dict and list
        pos_items = positions.values() if isinstance(positions, dict) else positions
        for pos_data in pos_items:
            if not isinstance(pos_data, dict):
                continue
            depths = pos_data.get('depths', {})
            for depth_data in depths.values():
                if isinstance(depth_data, dict) and 'time' in depth_data:
                    times.append(depth_data['time'])
        
        if times:
            avg_time = sum(times) / len(times)
    
    return total, passed, failed, avg_time, avg_nps


def extract_puzzle_metrics(content: Dict[str, Any]) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[float], Optional[str], List[str]]:
    """
    Extract metrics from puzzle analysis.
    
    Returns:
        (total_tests, passed_tests, failed_tests, avg_accuracy, rating_range, themes)
    """
    results = content.get('analysis_results', [])
    
    if not results:
        return None, None, None, None, None, []
    
    total = len(results)
    
    # Count perfect sequences as passed
    passed = sum(1 for r in results if r.get('perfect_sequence', False))
    failed = total - passed
    
    # Calculate average accuracy
    accuracies = [r.get('sequence_accuracy_weighted', 0) for r in results if 'sequence_accuracy_weighted' in r]
    avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else None
    
    # Extract rating range
    ratings = [r.get('rating') for r in results if 'rating' in r]
    rating_range = f"{min(ratings)}-{max(ratings)}" if ratings else None
    
    # Extract unique themes
    all_themes = set()
    for result in results:
        themes_data = result.get('themes', '')
        if isinstance(themes_data, list):
            # Already a list
            all_themes.update(themes_data)
        elif isinstance(themes_data, str) and themes_data:
            # String - split by spaces
            themes_list = themes_data.split()
            all_themes.update(themes_list)
    
    return total, passed, failed, avg_accuracy, rating_range, list(all_themes)


def parse_analysis_file(blob: storage.Blob, content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse analysis JSON and extract structured fields.
    
    Args:
        blob: GCS blob object
        content: Parsed JSON content
        
    Returns:
        Record ready for BigQuery insertion
    """
    file_path = f"gs://{blob.bucket.name}/{blob.name}"
    file_name = blob.name.split('/')[-1]
    
    # Generate ID
    analysis_id = generate_analysis_id(file_path)
    
    # Classify type
    analysis_type = classify_analysis_type(file_name)
    
    # Extract version
    engine_version = extract_engine_version(file_name, content)
    
    # Extract timestamp
    test_timestamp = None
    if 'test_timestamp' in content:
        try:
            test_timestamp = datetime.fromisoformat(content['test_timestamp']).isoformat()
        except:
            pass
    elif 'timestamp' in content:
        try:
            test_timestamp = datetime.fromisoformat(content['timestamp']).isoformat()
        except:
            pass
    
    # Extract type-specific metrics
    total_tests = None
    passed_tests = None
    failed_tests = None
    success_rate = None
    avg_time_seconds = None
    avg_nps = None
    rating_range = None
    themes = []
    opponent_engine = None
    summary_text = None
    
    if analysis_type == 'perft':
        total_tests, passed_tests, failed_tests, avg_time_seconds, avg_nps = extract_perft_metrics(content)
    elif analysis_type in ['puzzle', 'tactical']:
        total_tests, passed_tests, failed_tests, avg_accuracy, rating_range, themes = extract_puzzle_metrics(content)
        success_rate = avg_accuracy  # Use accuracy as success_rate for puzzles
    elif analysis_type == 'comparison':
        opponent_engine = extract_opponent_engine(file_name, content)
    
    # Calculate success rate if not set
    if success_rate is None and total_tests and total_tests > 0 and passed_tests is not None:
        success_rate = (passed_tests / total_tests) * 100.0
    
    # Build summary text
    if analysis_type == 'perft':
        summary_text = f"Perft test: {passed_tests}/{total_tests} passed" if total_tests else None
    elif analysis_type in ['puzzle', 'tactical']:
        summary_text = f"Puzzle analysis: {success_rate:.1f}% accuracy, {total_tests} puzzles" if success_rate and total_tests else None
    
    # Build record
    record = {
        'analysis_id': analysis_id,
        'file_path': file_path,
        'file_name': file_name,
        'analysis_type': analysis_type,
        'engine_version': engine_version,
        'test_timestamp': test_timestamp,
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'success_rate': success_rate,
        'avg_time_seconds': avg_time_seconds,
        'avg_nps': avg_nps,
        'rating_range': rating_range,
        'themes': themes if themes else [],  # Empty array instead of None
        'opponent_engine': opponent_engine,
        'summary_text': summary_text,
        'content_json': content,
        'file_size_bytes': blob.size,
        'ingested_at': datetime.utcnow().isoformat()
    }
    
    return record


def fetch_analysis_files(storage_client: storage.Client, limit: Optional[int] = None) -> List[Tuple[storage.Blob, Dict[str, Any]]]:
    """
    Fetch all analysis JSON files from GCS.
    
    Args:
        storage_client: GCS storage client
        limit: Maximum number of files to process (for testing)
        
    Returns:
        List of (blob, parsed_json) tuples
    """
    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = bucket.list_blobs(prefix=SOURCE_PREFIX)
    
    files = []
    count = 0
    
    for blob in blobs:
        if not blob.name.endswith('.json'):
            continue
        
        logger.info(f"Fetching {blob.name}")
        
        try:
            content = blob.download_as_text()
            parsed = json.loads(content)
            files.append((blob, parsed))
            count += 1
            
            if limit and count >= limit:
                logger.info(f"Reached limit of {limit} files")
                break
        except Exception as e:
            logger.error(f"Failed to parse {blob.name}: {e}")
            continue
    
    logger.info(f"Fetched {len(files)} JSON files")
    return files


def ingest_analysis_results(dry_run: bool = False, limit: Optional[int] = None) -> None:
    """
    Main ingestion function.
    
    Args:
        dry_run: If True, parse data but don't insert to BigQuery
        limit: Maximum number of files to process
    """
    logger.info("Starting analysis results ingestion")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    if limit:
        logger.info(f"Limit: {limit} files")
    
    # Initialize clients
    bq_client = bigquery.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)
    
    # Verify target table exists
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TARGET_TABLE}"
    try:
        table = bq_client.get_table(table_ref)
        logger.info(f"Table {table_ref} exists")
    except Exception:
        logger.error(f"Table {table_ref} not found!")
        logger.error("Run 'terraform apply' first")
        raise
    
    # Fetch and parse files
    files = fetch_analysis_files(storage_client, limit=limit)
    
    if not files:
        logger.warning("No JSON files found")
        return
    
    # Parse all files
    records = []
    for blob, content in files:
        try:
            record = parse_analysis_file(blob, content)
            records.append(record)
            logger.info(f"Parsed: {record['file_name']} -> type={record['analysis_type']}, version={record['engine_version']}")
        except Exception as e:
            logger.error(f"Failed to parse {blob.name}: {e}", exc_info=True)
            continue
    
    logger.info(f"Parsed {len(records)} analysis files")
    
    if dry_run:
        logger.info("DRY RUN - Skipping BigQuery insert")
        
        # Show type breakdown
        type_counts = {}
        for record in records:
            type_counts[record['analysis_type']] = type_counts.get(record['analysis_type'], 0) + 1
        
        logger.info("Analysis type breakdown:")
        for atype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            logger.info(f"  {atype}: {count}")
        
        logger.info(f"Sample record: {records[0]}")
        return
    
    # Insert to BigQuery using load_table_from_json (more reliable for large batches)
    logger.info(f"Inserting {len(records)} rows to BigQuery using load_table_from_json...")
    
    # Configure load job
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    
    # Load data
    load_job = bq_client.load_table_from_json(
        records,
        table,
        job_config=job_config
    )
    
    # Wait for job to complete
    logger.info("Waiting for load job to complete...")
    load_job.result()  # Blocks until job is done
    
    logger.info(f"✅ Successfully ingested {len(records)} analysis results")
    
    # Query to verify
    query = f"""
        SELECT 
            analysis_type,
            COUNT(*) as count,
            COUNT(DISTINCT engine_version) as versions,
            MIN(test_timestamp) as earliest,
            MAX(test_timestamp) as latest
        FROM `{PROJECT_ID}.{DATASET_ID}.{TARGET_TABLE}`
        GROUP BY analysis_type
        ORDER BY count DESC
    """
    
    logger.info("Verifying ingestion:")
    results = bq_client.query(query).result()
    
    for row in results:
        logger.info(f"  {row.analysis_type}: {row.count} files, "
                   f"{row.versions} versions, earliest={row.earliest}, latest={row.latest}")


def main():
    """Main entry point."""
    dry_run = '--dry-run' in sys.argv
    
    # Parse limit argument
    limit = None
    for arg in sys.argv:
        if arg.startswith('--limit='):
            limit = int(arg.split('=')[1])
    
    try:
        ingest_analysis_results(dry_run=dry_run, limit=limit)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
