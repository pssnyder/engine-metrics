#!/usr/bin/env python3
"""
Documentation Ingestion Script
Loads V7P3R markdown documentation from GCS to BigQuery

Usage:
    python 01_ingest_documentation.py [--dry-run]
"""

import hashlib
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from google.cloud import storage, bigquery
from google.cloud.exceptions import NotFound

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "chess-engine-metrics-agent"
BUCKET_NAME = "v7p3r-raw-data"
GCS_PREFIX = "v7p3r_docs/"
DATASET_ID = "conformed_layer"
TABLE_ID = "documentation"


def generate_doc_id(file_path: str) -> str:
    """Generate unique doc_id from file path using SHA256 hash."""
    return hashlib.sha256(file_path.encode()).hexdigest()[:16]


def categorize_document(file_path: str) -> str:
    """Categorize document based on file path."""
    path_lower = file_path.lower()
    
    if 'archive' in path_lower:
        return 'archive'
    elif 'config' in path_lower or 'settings' in path_lower:
        return 'configuration'
    elif 'deploy' in path_lower or 'production' in path_lower:
        return 'deployment'
    elif 'dev' in path_lower or 'roadmap' in path_lower or 'phase' in path_lower:
        return 'development'
    elif 'test' in path_lower:
        return 'testing'
    elif 'changelog' in path_lower or 'version' in path_lower:
        return 'changelog'
    elif 'readme' in path_lower or 'quickstart' in path_lower or 'getting-started' in path_lower:
        return 'guide'
    else:
        return 'general'


def process_markdown_file(blob: storage.Blob) -> Dict[str, Any]:
    """
    Process a single markdown file from GCS.
    
    Args:
        blob: GCS blob object
        
    Returns:
        Dictionary with all fields for BigQuery row
    """
    # Download content
    content = blob.download_as_text(encoding='utf-8')
    
    # Calculate metadata
    file_path = blob.name.replace(GCS_PREFIX, '')
    file_name = Path(file_path).name
    line_count = content.count('\n') + 1
    word_count = len(content.split())
    
    return {
        'doc_id': generate_doc_id(file_path),
        'file_path': file_path,
        'file_name': file_name,
        'category': categorize_document(file_path),
        'content': content,
        'file_size_bytes': blob.size,
        'line_count': line_count,
        'word_count': word_count,
        'gcs_uri': f"gs://{BUCKET_NAME}/{blob.name}",
        'file_modified_at': blob.updated.isoformat() if blob.updated else None,
        'ingested_at': datetime.utcnow().isoformat()
    }


def fetch_documentation_files(storage_client: storage.Client) -> List[storage.Blob]:
    """
    Fetch all markdown files from GCS bucket.
    
    Args:
        storage_client: GCS client
        
    Returns:
        List of GCS blob objects
    """
    logger.info(f"Fetching files from gs://{BUCKET_NAME}/{GCS_PREFIX}")
    
    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = list(bucket.list_blobs(prefix=GCS_PREFIX))
    
    # Filter for markdown files only
    markdown_blobs = [
        blob for blob in blobs 
        if blob.name.endswith('.md') and not blob.name.endswith('/')
    ]
    
    logger.info(f"Found {len(markdown_blobs)} markdown files")
    return markdown_blobs


def create_table_if_not_exists(bq_client: bigquery.Client) -> bigquery.Table:
    """
    Check if table exists, error if it doesn't (Terraform should create it).
    
    Args:
        bq_client: BigQuery client
        
    Returns:
        BigQuery table object
        
    Raises:
        NotFound: If table doesn't exist (Terraform hasn't been applied)
    """
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    
    try:
        table = bq_client.get_table(table_ref)
        logger.info(f"Table {table_ref} exists")
        return table
    except NotFound:
        logger.error(f"Table {table_ref} not found!")
        logger.error("Run 'terraform apply' first to create the schema")
        raise


def ingest_documentation(dry_run: bool = False) -> None:
    """
    Main ingestion function.
    
    Args:
        dry_run: If True, process files but don't insert to BigQuery
    """
    logger.info("Starting documentation ingestion")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    
    # Initialize clients
    storage_client = storage.Client(project=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID)
    
    # Verify table exists
    table = create_table_if_not_exists(bq_client)
    
    # Fetch all documentation files
    blobs = fetch_documentation_files(storage_client)
    
    if not blobs:
        logger.warning("No markdown files found to ingest")
        return
    
    # Process each file
    rows_to_insert = []
    for i, blob in enumerate(blobs, 1):
        logger.info(f"Processing {i}/{len(blobs)}: {blob.name}")
        
        try:
            row = process_markdown_file(blob)
            rows_to_insert.append(row)
        except Exception as e:
            logger.error(f"Failed to process {blob.name}: {e}")
            continue
    
    logger.info(f"Processed {len(rows_to_insert)} files successfully")
    
    if dry_run:
        logger.info("DRY RUN - Skipping BigQuery insert")
        logger.info(f"Sample row: {rows_to_insert[0] if rows_to_insert else 'None'}")
        return
    
    # Insert to BigQuery
    logger.info(f"Inserting {len(rows_to_insert)} rows to BigQuery...")
    
    errors = bq_client.insert_rows_json(table, rows_to_insert)
    
    if errors:
        logger.error(f"Errors inserting rows: {errors}")
        raise RuntimeError(f"BigQuery insert failed: {errors}")
    
    logger.info(f"✅ Successfully ingested {len(rows_to_insert)} documentation files")
    
    # Query to verify
    query = f"""
        SELECT 
            category,
            COUNT(*) as count,
            SUM(file_size_bytes) as total_bytes,
            SUM(word_count) as total_words
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        GROUP BY category
        ORDER BY count DESC
    """
    
    logger.info("Verifying ingestion:")
    results = bq_client.query(query).result()
    
    for row in results:
        logger.info(f"  {row.category}: {row.count} files, {row.total_bytes:,} bytes, {row.total_words:,} words")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    
    try:
        ingest_documentation(dry_run=dry_run)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)
