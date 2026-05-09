#!/usr/bin/env python3
"""
Operational Events Ingestion Script
Extracts operational events from notation_events.json

Usage:
    python 03_ingest_operational_events.py [--dry-run]
"""

import hashlib
import json
import logging
import sys
from datetime import datetime, date
from typing import List, Dict, Any, Optional

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
TARGET_TABLE = "operational_events"
BUCKET_NAME = "v7p3r-raw-data"
SOURCE_FILE = "notation_events.json"


def generate_event_id(event_date: str, title: str) -> str:
    """
    Generate unique event ID from date and title.
    
    Args:
        event_date: Event date string
        title: Event title
        
    Returns:
        SHA256 hash (first 16 chars) as event ID
    """
    content = f"{event_date}::{title}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string
        
    Returns:
        Python date object or None
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception as e:
        logger.warning(f"Could not parse date: {date_str} - {e}")
        return None


def extract_events(json_content: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract events from notation_events.json structure.
    
    Args:
        json_content: Parsed JSON content
        
    Returns:
        List of event records ready for BigQuery
    """
    events = []
    
    if 'events' not in json_content:
        logger.error("No 'events' key found in JSON")
        return events
    
    for event in json_content['events']:
        # Parse required fields
        event_date_str = event.get('date')
        if not event_date_str:
            logger.warning(f"Event missing date, skipping: {event.get('title', 'NO TITLE')}")
            continue
        
        event_date = parse_date(event_date_str)
        if not event_date:
            continue
        
        title = event.get('title', '')
        if not title:
            logger.warning(f"Event missing title, skipping: {event_date_str}")
            continue
        
        event_type = event.get('type', '')
        if not event_type:
            logger.warning(f"Event missing type, skipping: {title}")
            continue
        
        description = event.get('description', '')
        if not description:
            logger.warning(f"Event missing description, skipping: {title}")
            continue
        
        # Generate event ID
        event_id = generate_event_id(event_date_str, title)
        
        # Collect additional metadata fields not in main schema
        metadata = {}
        known_fields = {
            'date', 'date_approximate', 'type', 'title', 'change_scope',
            'engine_version_affected', 'description', 'expected_metric_impact',
            'engine_regression', 'root_cause', 'action_taken', 'status',
            'bug_mechanism', 'active_period', 'validation_period',
            'related_changelog_entry', 'notes'
        }
        
        for key, value in event.items():
            if key not in known_fields and value is not None:
                metadata[key] = value
        
        # Build record
        event_record = {
            'event_id': event_id,
            'event_date': event_date.isoformat(),
            'date_approximate': event.get('date_approximate', False),
            'event_type': event_type,
            'title': title,
            'change_scope': event.get('change_scope'),
            'engine_version_affected': event.get('engine_version_affected'),
            'description': description,
            'expected_metric_impact': event.get('expected_metric_impact'),
            'engine_regression': event.get('engine_regression'),
            'root_cause': event.get('root_cause'),
            'action_taken': event.get('action_taken'),
            'status': event.get('status'),
            'bug_mechanism': event.get('bug_mechanism'),
            'active_period': event.get('active_period'),
            'validation_period': event.get('validation_period'),
            'related_changelog_entry': event.get('related_changelog_entry'),
            'notes': event.get('notes'),
            'metadata': metadata if metadata else None,
            'ingested_at': datetime.utcnow().isoformat()
        }
        
        events.append(event_record)
        logger.info(f"Parsed event: {event_date} - {title}")
    
    logger.info(f"Extracted {len(events)} event records")
    return events


def fetch_json_from_gcs(storage_client: storage.Client) -> Dict[str, Any]:
    """
    Fetch notation_events.json from GCS bucket.
    
    Args:
        storage_client: GCS storage client
        
    Returns:
        Parsed JSON content
    """
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(SOURCE_FILE)
    
    logger.info(f"Fetching {SOURCE_FILE} from gs://{BUCKET_NAME}/")
    content = blob.download_as_text()
    
    logger.info(f"Downloaded {len(content)} bytes")
    return json.loads(content)


def create_table_if_not_exists(bq_client: bigquery.Client) -> bigquery.Table:
    """
    Check if table exists.
    
    Args:
        bq_client: BigQuery client
        
    Returns:
        BigQuery table object
    """
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TARGET_TABLE}"
    
    try:
        table = bq_client.get_table(table_ref)
        logger.info(f"Table {table_ref} exists")
        return table
    except Exception:
        logger.error(f"Table {table_ref} not found!")
        logger.error("Run 'terraform apply' first to create the schema")
        raise


def ingest_operational_events(dry_run: bool = False) -> None:
    """
    Main ingestion function.
    
    Args:
        dry_run: If True, parse data but don't insert to BigQuery
    """
    logger.info("Starting operational events ingestion")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    
    # Initialize clients
    bq_client = bigquery.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)
    
    # Verify target table exists
    table = create_table_if_not_exists(bq_client)
    
    # Fetch JSON from GCS
    json_content = fetch_json_from_gcs(storage_client)
    
    # Parse events
    events = extract_events(json_content)
    
    if not events:
        logger.warning("No events extracted")
        return
    
    if dry_run:
        logger.info("DRY RUN - Skipping BigQuery insert")
        logger.info(f"Sample records: {events[:2]}")
        return
    
    # Insert to BigQuery
    logger.info(f"Inserting {len(events)} rows to BigQuery...")
    
    errors = bq_client.insert_rows_json(table, events)
    
    if errors:
        logger.error(f"Errors inserting rows: {errors}")
        raise RuntimeError(f"BigQuery insert failed: {errors}")
    
    logger.info(f"✅ Successfully ingested {len(events)} operational events")
    
    # Query to verify
    query = f"""
        SELECT 
            event_type,
            COUNT(*) as count,
            MIN(event_date) as earliest,
            MAX(event_date) as latest
        FROM `{PROJECT_ID}.{DATASET_ID}.{TARGET_TABLE}`
        GROUP BY event_type
        ORDER BY count DESC
    """
    
    logger.info("Verifying ingestion:")
    results = bq_client.query(query).result()
    
    for row in results:
        logger.info(f"  {row.event_type}: {row.count} events, "
                   f"earliest={row.earliest}, latest={row.latest}")


def main():
    """Main entry point."""
    dry_run = '--dry-run' in sys.argv
    
    try:
        ingest_operational_events(dry_run=dry_run)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
