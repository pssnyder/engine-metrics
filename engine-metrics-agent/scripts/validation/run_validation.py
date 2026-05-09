#!/usr/bin/env python3
"""
Validation Query Executor

Execute SQL validation queries against BigQuery and display results.
"""

import os
import sys
from pathlib import Path
from google.cloud import bigquery
import pandas as pd

# Configuration
PROJECT_ID = "chess-engine-metrics-agent"
VALIDATION_DIR = Path(__file__).parent

def run_query(client, sql_file, description):
    """Execute a SQL file and display results"""
    print("=" * 80)
    print(f"{description}")
    print("=" * 80)
    
    sql_path = VALIDATION_DIR / sql_file
    if not sql_path.exists():
        print(f"ERROR: SQL file not found: {sql_path}")
        return None
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        query = f.read()
    
    print(f"Executing: {sql_file}")
    print("-" * 80)
    
    try:
        df = client.query(query).to_dataframe()
        print(f"\nResults ({len(df)} rows):")
        print(df.to_string(index=False))
        print()
        return df
    except Exception as e:
        print(f"ERROR: Query failed - {e}")
        return None


def main():
    """Run all validation queries"""
    print("V7P3R ENGINE METRICS VALIDATION FRAMEWORK")
    print("=" * 80)
    print(f"Project: {PROJECT_ID}")
    print(f"Validation Directory: {VALIDATION_DIR}")
    print()
    
    # Initialize BigQuery client
    try:
        client = bigquery.Client(project=PROJECT_ID)
        print("[OK] BigQuery client initialized\n")
    except Exception as e:
        print(f"[FAIL] Failed to initialize BigQuery client: {e}")
        sys.exit(1)
    
    # Query 1: Check for duplicates
    duplicates_df = run_query(
        client,
        "01_check_duplicates.sql",
        "DUPLICATE DETECTION ANALYSIS"
    )
    
    if duplicates_df is not None:
        total_duplicates = duplicates_df['inflated_count'].sum()
        if total_duplicates > 0:
            print(f"⚠️  WARNING: Found {total_duplicates} duplicate records!")
            print("   These will inflate metrics and need deduplication.")
        else:
            print("✓ No duplicates found - metrics are clean")
    
    input("\nPress Enter to continue to opponent-adjusted analysis...")
    
    # Query 2: Opponent-adjusted performance
    performance_df = run_query(
        client,
        "02_opponent_adjusted_performance.sql",
        "OPPONENT-ADJUSTED PERFORMANCE ANALYSIS"
    )
    
    if performance_df is not None:
        print("\nKEY INSIGHTS:")
        print(f"  - Total versions analyzed: {len(performance_df)}")
        if len(performance_df) > 0:
            best_raw = performance_df.nlargest(1, 'raw_win_rate').iloc[0]
            best_adjusted = performance_df.nlargest(1, 'quality_adjusted_win_rate').iloc[0]
            print(f"  - Best raw win rate: {best_raw['engine_version']} ({best_raw['raw_win_rate']:.2%})")
            print(f"  - Best quality-adjusted: {best_adjusted['engine_version']} ({best_adjusted['quality_adjusted_win_rate']:.2%})")
            
            if best_raw['engine_version'] != best_adjusted['engine_version']:
                print("\n⚠️  NOTE: Different versions rank best by raw vs adjusted metrics!")
                print("    Use quality_adjusted_win_rate for accurate comparison.")
    
    input("\nPress Enter to continue to strongest version analysis...")
    
    # Query 3: Strongest version ranking
    strongest_df = run_query(
        client,
        "03_strongest_version_analysis.sql",
        "STRONGEST V7P3R VERSION RANKING"
    )
    
    if strongest_df is not None and len(strongest_df) > 0:
        print("\n" + "=" * 80)
        print("🏆 ANSWER: WHICH V7P3R VERSION IS STRONGEST?")
        print("=" * 80)
        
        strongest = strongest_df.iloc[0]
        print(f"\n✨ STRONGEST VERSION: {strongest['engine_version']}")
        print(f"   Composite Strength Score: {strongest['composite_strength_score']:.2f}/100")
        print(f"   Quality-Adjusted Win Rate: {strongest['quality_adjusted_win_rate']:.2%}")
        print(f"   Performance vs Expected: {strongest['performance_vs_expected']:+.4f}")
        print(f"   Average ELO: {strongest['avg_elo']:.0f}")
        print(f"   Peak ELO: {strongest['peak_elo']:.0f}")
        print(f"   Sample Size: {strongest['total_games']} games")
        print(f"   Confidence: {strongest['confidence_level']}")
        print(f"\n   Active Period: {strongest['first_game_date']} to {strongest['last_game_date']}")
        print(f"   Record: {strongest['wins']}W-{strongest['losses']}L-{strongest['draws']}D")
        
        if len(strongest_df) > 1:
            print("\n   Top 5 Versions by Composite Strength:")
            for idx, row in strongest_df.head(5).iterrows():
                print(f"   {int(row['overall_rank'])}. {row['engine_version']:<10} "
                      f"(Score: {row['composite_strength_score']:.1f}, "
                      f"Win Rate: {row['quality_adjusted_win_rate']:.2%}, "
                      f"{row['total_games']} games)")
    
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
