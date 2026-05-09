#!/usr/bin/env python3
"""
Engine Versions Ingestion Script
Extracts version history from CHANGELOG.md in BigQuery documentation table

Usage:
    python 02_ingest_engine_versions.py [--dry-run]
"""

import logging
import re
import sys
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from google.cloud import bigquery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "chess-engine-metrics-agent"
DATASET_ID = "conformed_layer"
SOURCE_TABLE = "documentation"
TARGET_TABLE = "engine_versions"


def parse_version_string(version_str: str) -> Dict[str, Optional[int]]:
    """
    Parse version string like 'v18.0' or 'v17.1.1' into components.
    
    Args:
        version_str: Version string (e.g., 'v17.1', 'v18.0')
        
    Returns:
        Dict with major, minor, patch
    """
    # Remove 'v' prefix and split
    clean = version_str.lstrip('v')
    parts = clean.split('.')
    
    return {
        'major': int(parts[0]) if len(parts) > 0 else 0,
        'minor': int(parts[1]) if len(parts) > 1 else 0,
        'patch': int(parts[2]) if len(parts) > 2 else None
    }


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse date string in various formats.
    
    Args:
        date_str: Date string like '2025-12-29' or '2025-11-26 to 2025-11-30'
        
    Returns:
        Python date object or None
    """
    # Handle date ranges - take first date
    if ' to ' in date_str:
        date_str = date_str.split(' to ')[0].strip()
    
    # Try parsing YYYY-MM-DD
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        pass
    
    # Try parsing 2025-11-26+ (remove +)
    if date_str.endswith('+'):
        try:
            return datetime.strptime(date_str.rstrip('+'), '%Y-%m-%d').date()
        except:
            pass
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


def extract_field_value(lines: List[str], field_name: str, default: Any = None) -> Any:
    """
    Extract a field value from markdown list lines.
    
    Args:
        lines: List of markdown lines
        field_name: Field name to extract (e.g., 'Deployed', 'Status')
        default: Default value if not found
        
    Returns:
        Field value as string
    """
    pattern = fr'^\s*-\s+\*\*{re.escape(field_name)}\*\*:\s+(.+)$'
    
    for line in lines:
        match = re.match(pattern, line)
        if match:
            return match.group(1).strip()
    
    return default


def extract_list_items(lines: List[str], field_name: str) -> List[str]:
    """
    Extract list items from a field like Features or Known Issues.
    
    Args:
        lines: List of markdown lines
        field_name: Field name (e.g., 'Features', 'Known Issues')
        
    Returns:
        List of items
    """
    items = []
    in_list = False
    
    for line in lines:
        # Check for field header
        if f'**{field_name}**:' in line:
            # Check if the value is on the same line (e.g., "**Features**: []" or "**Known Issues**: []")
            if line.strip().endswith('[]'):
                return []  # Empty list indicator
            in_list = True
            continue
        
        # If we're in the list, collect items
        if in_list:
            # Check if this is a sub-item (indented list item)
            if line.strip().startswith('- ') and not line.strip().startswith('- **'):
                items.append(line.strip().lstrip('- ').strip())
            # Check if this is the next field (starts with - **)
            elif line.strip().startswith('- **'):
                break
            # Check if we hit an empty line or new section
            elif not line.strip():
                break
    
    return items


def extract_version_data(changelog_content: str) -> List[Dict[str, Any]]:
    """
    Extract version deployment data from new structured CHANGELOG.md format.
    
    New format example:
        ### v18.4
        - **Deployed**: 2026-04-17
        - **Retired**: [ACTIVE]
        - **Status**: active
        - **Rollback**: false
        - **Duration Days**: [TBD]
        - **Deployment Method**: automated
        - **Environment**: production
        - **ELO Rating**: [TBD]
        - **Games Played**: [TBD]
        - **Features**:
          - Feature 1
        - **Known Issues**: []
        - **Rollback Reason**: N/A
        - **Notes**: Additional context
    
    Args:
        changelog_content: Full CHANGELOG.md markdown text
        
    Returns:
        List of version records
    """
    versions = []
    
    # Split content into sections by ### headers
    sections = re.split(r'\n###\s+', changelog_content)
    logger.info(f"Split changelog into {len(sections)} sections")
    
    for idx, section in enumerate(sections):
        # Check if this section starts with a version (vX.X)
        version_match = re.match(r'^(v[\d.]+)\s*\n', section)
        if not version_match:
            # Debug: show first 100 chars of non-matching section
            logger.debug(f"Section {idx} did not match version pattern: {section[:100]!r}")
            continue
        
        version_str = version_match.group(1)
        
        # Split section into lines for parsing
        lines = section.split('\n')
        
        # Extract all fields
        deployed_str = extract_field_value(lines, 'Deployed')
        retired_str = extract_field_value(lines, 'Retired')
        status_str = extract_field_value(lines, 'Status', 'retired')
        rollback_str = extract_field_value(lines, 'Rollback', 'false')
        duration_str = extract_field_value(lines, 'Duration Days')
        method_str = extract_field_value(lines, 'Deployment Method', 'automated')
        environment_str = extract_field_value(lines, 'Environment', 'production')
        elo_str = extract_field_value(lines, 'ELO Rating')
        games_str = extract_field_value(lines, 'Games Played')
        rollback_reason = extract_field_value(lines, 'Rollback Reason')
        notes = extract_field_value(lines, 'Notes')
        
        # Extract lists
        features = extract_list_items(lines, 'Features')
        known_issues = extract_list_items(lines, 'Known Issues')
        
        # Parse dates
        deployed_at = None
        if deployed_str and deployed_str not in ['[ACTIVE]', '[TBD]', '[UNKNOWN]', 'N/A']:
            deployed_at = parse_date(deployed_str)
        
        retired_at = None
        if retired_str and retired_str not in ['[ACTIVE]', '[TBD]', '[UNKNOWN]', 'N/A']:
            retired_at = parse_date(retired_str)
        
        # Parse rollback boolean
        rollback = rollback_str.lower() in ['true', 'yes', '1']
        
        # Parse duration
        deployment_duration = None
        if duration_str and duration_str not in ['[TBD]', '[UNKNOWN]', 'N/A']:
            try:
                deployment_duration = int(duration_str)
            except ValueError:
                pass
        elif deployed_at and retired_at:
            # Calculate if both dates present
            deployment_duration = (retired_at - deployed_at).days
        
        # Parse ELO
        elo_rating = None
        if elo_str and elo_str not in ['[TBD]', '[UNKNOWN]', 'N/A']:
            try:
                elo_rating = int(elo_str)
            except ValueError:
                pass
        
        # Parse games played
        games_played = None
        if games_str and games_str not in ['[TBD]', '[UNKNOWN]', 'N/A']:
            try:
                games_played = int(games_str)
            except ValueError:
                pass
        
        # Clean rollback reason and notes
        if rollback_reason and rollback_reason in ['N/A', '[TBD]', '[UNKNOWN]']:
            rollback_reason = None
        if notes and notes in ['N/A', '[TBD]', '[UNKNOWN]']:
            notes = None
        
        # Parse version components
        version_parts = parse_version_string(version_str)
        
        version_record = {
            'version_id': version_str,
            'version_major': version_parts['major'],
            'version_minor': version_parts['minor'],
            'version_patch': version_parts['patch'],
            'deployed_at': deployed_at.isoformat() if deployed_at else None,
            'retired_at': retired_at.isoformat() if retired_at else None,
            'deployment_duration_days': deployment_duration,
            'status': status_str.lower() if status_str else 'retired',
            'rollback': rollback,
            'rollback_reason': rollback_reason,
            'deployment_method': method_str.lower() if method_str else 'automated',
            'gcp_instance': 'v7p3r-production-bot',
            'notes': notes,
            'major_features': features if features else [],
            'known_issues': known_issues if known_issues else [],
            'elo_rating': elo_rating,
            'games_played': games_played,
            'ingested_at': datetime.utcnow().isoformat()
        }
        
        versions.append(version_record)
        logger.info(f"Parsed version: {version_str} (deployed={deployed_at}, status={status_str})")
    
    logger.info(f"Extracted {len(versions)} version records")
    return versions


def fetch_changelog_content(bq_client: bigquery.Client) -> str:
    """
    Fetch CHANGELOG.md content from documentation table.
    
    Args:
        bq_client: BigQuery client
        
    Returns:
        CHANGELOG.md content as string
    """
    query = f"""
        SELECT content
        FROM `{PROJECT_ID}.{DATASET_ID}.{SOURCE_TABLE}`
        WHERE file_name = 'CHANGELOG.md'
        ORDER BY ingested_at DESC
        LIMIT 1
    """
    
    logger.info("Fetching latest CHANGELOG.md from documentation table...")
    results = bq_client.query(query).result()
    
    for row in results:
        logger.info("CHANGELOG.md found")
        return row.content
    
    raise ValueError("CHANGELOG.md not found in documentation table")


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


def ingest_engine_versions(dry_run: bool = False) -> None:
    """
    Main ingestion function.
    
    Args:
        dry_run: If True, parse data but don't insert to BigQuery
    """
    logger.info("Starting engine versions ingestion")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    
    # Initialize client
    bq_client = bigquery.Client(project=PROJECT_ID)
    
    # Verify target table exists
    table = create_table_if_not_exists(bq_client)
    
    # Fetch CHANGELOG content
    changelog_content = fetch_changelog_content(bq_client)
    
    # Parse version data
    versions = extract_version_data(changelog_content)
    
    # Filter out versions with no deployment date (can't be ingested)
    versions_with_dates = [v for v in versions if v['deployed_at'] is not None]
    skipped = len(versions) - len(versions_with_dates)
    
    if skipped > 0:
        logger.info(f"Skipped {skipped} versions with no deployment date")
    
    if not versions_with_dates:
        logger.warning("No version data with valid dates extracted")
        return
    
    logger.info(f"Extracted {len(versions_with_dates)} version records with valid dates")
    
    if dry_run:
        logger.info("DRY RUN - Skipping BigQuery insert")
        logger.info(f"Sample records: {versions_with_dates[:3]}")
        return
    
    # Insert to BigQuery
    logger.info(f"Inserting {len(versions_with_dates)} rows to BigQuery...")
    
    errors = bq_client.insert_rows_json(table, versions_with_dates)
    
    if errors:
        logger.error(f"Errors inserting rows: {errors}")
        raise RuntimeError(f"BigQuery insert failed: {errors}")
    
    logger.info(f"✅ Successfully ingested {len(versions_with_dates)} engine versions")
    
    # Query to verify
    query = f"""
        SELECT 
            status,
            COUNT(*) as count,
            MIN(deployed_at) as earliest,
            MAX(deployed_at) as latest,
            AVG(deployment_duration_days) as avg_duration_days
        FROM `{PROJECT_ID}.{DATASET_ID}.{TARGET_TABLE}`
        GROUP BY status
        ORDER BY count DESC
    """
    
    logger.info("Verifying ingestion:")
    results = bq_client.query(query).result()
    
    for row in results:
        avg_dur = f"{row.avg_duration_days:.1f}" if row.avg_duration_days is not None else "N/A"
        logger.info(f"  {row.status}: {row.count} versions, "
                   f"earliest={row.earliest}, latest={row.latest}, "
                   f"avg_duration={avg_dur} days")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    
    try:
        ingest_engine_versions(dry_run=dry_run)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)
