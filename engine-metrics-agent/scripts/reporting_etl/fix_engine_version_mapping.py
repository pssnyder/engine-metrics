#!/usr/bin/env python3
"""
Fix engine_version assignments in game_data using CHANGELOG deployment dates

This script corrects engine_version values for games played by v7p3r_bot
on Lichess by mapping game dates to the engine version that was deployed
at that time according to the CHANGELOG.

Source: conformed_layer.game_data
Reference: CHANGELOG.md deployment dates
Target: conformed_layer.game_data (UPDATE engine_version field)

Usage:
    python fix_engine_version_mapping.py                    # Full update
    python fix_engine_version_mapping.py --dry-run          # Preview changes only
"""

import argparse
import logging
import sys
from datetime import datetime, date
from google.cloud import bigquery

# Configuration
PROJECT_ID = "chess-engine-metrics-agent"
DATASET_ID = "conformed_layer"
TABLE_ID = "game_data"

# Version deployment periods from CHANGELOG.md
# Format: (version, deployed_date, retired_date)
VERSION_DEPLOYMENTS = [
    ('v18.4', date(2026, 4, 17), None),              # ACTIVE (no end date)
    ('v18.3', date(2025, 12, 29), date(2026, 4, 17)),
    ('v18.0', date(2025, 12, 20), date(2025, 12, 29)),
    ('v17.7', date(2025, 12, 6), date(2025, 12, 20)),
    ('v17.5', date(2025, 12, 2), date(2025, 12, 6)),
    ('v17.4', date(2025, 11, 26), date(2025, 11, 30)),  # Rolled back to v17.1
    ('v17.2.0', date(2025, 11, 21), date(2025, 11, 26)),
    ('v17.1.1', date(2025, 11, 21), date(2025, 11, 21)),  # Same-day deployment
    ('v17.1', date(2025, 11, 21), date(2025, 11, 21)),    # Initial, then re-deployed 11-30
    ('v17.0', date(2025, 11, 20), date(2025, 11, 21)),
    ('v16.1', date(2025, 11, 19), date(2025, 11, 20)),
    ('v14.1', date(2025, 10, 25), date(2025, 11, 19)),
    ('v14.0', date(2025, 10, 25), date(2025, 10, 25)),    # Same-day deployment
    ('v12.6', date(2025, 10, 4), date(2025, 10, 25)),
    ('v12.4', date(2025, 10, 3), date(2025, 10, 4)),
    ('v12.2', date(2025, 10, 3), date(2025, 10, 3)),      # Same-day deployment
]

# Special case: v17.1 was re-deployed as rollback target from v17.4
# Games from 2025-11-30 onwards (until v17.2.0) should be v17.1
# Need to handle this edge case

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_engine_version_mapping.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def build_version_mapping_case_statement():
    """Build SQL CASE statement to map dates to engine versions"""
    
    case_clauses = []
    
    for version, deployed, retired in VERSION_DEPLOYMENTS:
        if retired is None:
            # Active version (no end date)
            case_clauses.append(
                f"WHEN date >= '{deployed}' THEN '{version}'"
            )
        else:
            # Retired version (has end date)
            case_clauses.append(
                f"WHEN date >= '{deployed}' AND date < '{retired}' THEN '{version}'"
            )
    
    # Build full CASE statement
    case_statement = "CASE\n    " + "\n    ".join(case_clauses) + "\n    ELSE engine_version\n  END"
    
    return case_statement


def preview_changes(bq_client):
    """Preview what changes would be made"""
    logger.info("=" * 80)
    logger.info("DRY RUN - Previewing version mapping changes")
    logger.info("=" * 80)
    
    case_statement = build_version_mapping_case_statement()
    
    preview_query = f"""
    WITH corrected_versions AS (
      SELECT
        date,
        engine_version as old_version,
        {case_statement} as new_version
      FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    )
    
    SELECT
      old_version,
      new_version,
      MIN(date) as first_game,
      MAX(date) as last_game,
      COUNT(*) as games_affected
    FROM corrected_versions
    WHERE old_version != new_version
    GROUP BY old_version, new_version
    ORDER BY first_game
    """
    
    logger.info("Executing preview query...")
    results = bq_client.query(preview_query).to_dataframe()
    
    if len(results) == 0:
        logger.info("\n[OK] No changes needed - all versions already correct!")
        return 0
    
    logger.info(f"\nChanges that would be applied:")
    logger.info("-" * 80)
    logger.info(results.to_string(index=False))
    logger.info("-" * 80)
    logger.info(f"\nTotal games affected: {results['games_affected'].sum():,}")
    logger.info(f"Version corrections: {len(results)} distinct old->new mappings")
    
    return results['games_affected'].sum()


def apply_corrections(bq_client):
    """Apply engine version corrections to game_data table"""
    logger.info("=" * 80)
    logger.info("APPLYING VERSION CORRECTIONS")
    logger.info("=" * 80)
    
    case_statement = build_version_mapping_case_statement()
    
    update_query = f"""
    UPDATE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    SET engine_version = {case_statement}
    WHERE TRUE
    """
    
    logger.info("Executing UPDATE query...")
    logger.info("This may take a few minutes for large tables...")
    
    try:
        job = bq_client.query(update_query)
        result = job.result()
        
        rows_updated = job.num_dml_affected_rows
        logger.info(f"[OK] Updated {rows_updated:,} rows")
        logger.info(f"  - Bytes processed: {job.total_bytes_processed:,}")
        logger.info(f"  - Execution time: {job.ended - job.started}")
        
        return rows_updated
        
    except Exception as e:
        logger.error(f"Failed to update engine versions: {e}")
        raise


def validate_corrections(bq_client):
    """Validate that corrections were applied correctly"""
    logger.info("\nValidating corrections...")
    
    validation_query = f"""
    SELECT
      engine_version,
      COUNT(*) as games,
      MIN(date) as first_game,
      MAX(date) as last_game,
      DATE_DIFF(MAX(date), MIN(date), DAY) as duration_days
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE engine_version IS NOT NULL
    GROUP BY engine_version
    ORDER BY first_game
    """
    
    results = bq_client.query(validation_query).to_dataframe()
    
    logger.info("\nEngine version distribution after corrections:")
    logger.info("-" * 80)
    logger.info(results.to_string(index=False))
    logger.info("-" * 80)
    
    # Check for expected v18.x versions
    versions_found = set(results['engine_version'].tolist())
    expected_v18 = {'v18.0', 'v18.3', 'v18.4'}
    missing_v18 = expected_v18 - versions_found
    
    if missing_v18:
        logger.warning(f"\n[WARNING] Expected v18.x versions not found: {missing_v18}")
        logger.warning("This may indicate missing game data (not yet ingested)")
    else:
        logger.info(f"\n[OK] All expected v18.x versions found: {expected_v18 & versions_found}")
    
    # Check for v17.7
    if 'v17.7' not in versions_found:
        logger.warning("[WARNING] v17.7 not found (deployed 2025-12-06 to 2025-12-20)")
    else:
        logger.info("[OK] v17.7 found")
    
    return True


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Fix engine_version mappings using CHANGELOG dates")
    parser.add_argument('--dry-run', action='store_true', help="Preview changes without applying")
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Engine Version Mapping Correction Utility")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now()}")
    logger.info(f"Project: {PROJECT_ID}")
    logger.info(f"Target: {DATASET_ID}.{TABLE_ID}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'APPLY CORRECTIONS'}")
    logger.info(f"Version periods: {len(VERSION_DEPLOYMENTS)} defined")
    logger.info("=" * 80)
    
    # Initialize BigQuery client
    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
        logger.info("[OK] BigQuery client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize BigQuery client: {e}")
        sys.exit(1)
    
    try:
        # Preview changes
        affected_count = preview_changes(bq_client)
        
        if affected_count == 0:
            logger.info("\n[OK] No corrections needed")
            sys.exit(0)
        
        if args.dry_run:
            logger.info("\n[DRY RUN] No changes applied")
            logger.info("Run without --dry-run to apply these corrections")
        else:
            # Apply corrections
            logger.info("\nProceeding with corrections...")
            rows_updated = apply_corrections(bq_client)
            
            # Validate
            validate_corrections(bq_client)
        
        logger.info("=" * 80)
        logger.info("[OK] Completed successfully")
        logger.info(f"Finished: {datetime.now()}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"[FAIL] Operation failed: {e}")
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
