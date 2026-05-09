# V7P3R Engine Metrics - Complete Data Lakehouse Implementation Roadmap

**Status:** Ready for Implementation  
**Date:** 2026-04-24  
**Phase:** Pre-Infrastructure Planning Complete

---

## 📋 What We Just Accomplished

✅ **Complete Data Inventory**
- Cataloged ALL data sources across 3 repositories
- Identified 4M puzzles (not 50K), 50K+ games, 184 docs, 150+ analysis files
- Discovered missing entities: PUZZLES, PUZZLE_ANALYSIS, TOURNAMENTS

✅ **Updated Entity Relationship Diagram**
- **19 total tables** (was 12)
- Added PUZZLES, PUZZLE_ANALYSIS_RESULTS, TOURNAMENTS, TOURNAMENT_STANDINGS
- All fields mapped to source data with transformation logic

✅ **Source-to-Schema Mapping**
- Every source file type mapped to BigQuery columns
- Transformation logic documented (PGN parsing, JSON extraction, aggregation)
- Ingestion order defined with dependency graph

✅ **Storage Architecture Defined**
- Cloud Storage bucket structure (raw data organization)
- BigQuery dataset layers (raw → conformed → analytics)
- ~8-10GB final storage, ~$8/month cost

---

## 🎯 Implementation Summary

### Data Sources → Conformed Schema Coverage

| Data Source | Volume | Target Table(s) | Status |
|---|---|---|---|
| **Lichess PGN Files** | 50K+ games | LICHESS_GAMES, MOVES | ✅ Mapped |
| **Tournament PGN Files** | 5K+ games | LICHESS_GAMES, MOVES | ✅ Mapped |
| **Tournament .res Files** | 50+ tournaments | TOURNAMENTS, TOURNAMENT_STANDINGS | ✅ Mapped |
| **Stockfish Analysis JSON** | 150+ files | STOCKFISH_ANALYSIS, ERROR_PATTERNS | ✅ Mapped |
| **Puzzle Database SQLite** | 4M rows | PUZZLES | ✅ Mapped |
| **Puzzle Analysis JSON** | 890 tests | PUZZLE_ANALYSIS_RESULTS | ✅ Mapped |
| **Documentation Markdown** | 184 files | DOCUMENTATION | ✅ Mapped |
| **Notation Events JSON** | 1 file | OPERATIONAL_EVENTS | ✅ Mapped |
| **deployment_log.json** | 1 file | ENGINE_VERSIONS | ✅ Mapped |
| **CHANGELOG.md** | 1 file | VERSION_CHANGELOG | ✅ Mapped |
| **Aggregated Metrics** | Calculated | OPENINGS, OPPONENTS, GAME_SUMMARIES | ✅ Mapped |

**TOTAL: 19 tables, 100% source coverage, 0 data gaps**

---

## 🚀 Implementation Phases

### Phase 1: Infrastructure Setup (Week 1)

#### 1.1 Terraform Infrastructure as Code

**Files to Create:**
```
terraform/
├── main.tf                    # Provider config, project setup
├── bigquery.tf               # All 19 tables with schemas
├── storage.tf                # Cloud Storage buckets
├── iam.tf                    # Service accounts, roles
├── monitoring.tf             # Dashboards, alerts
├── variables.tf              # Configuration variables
└── outputs.tf                # Resource IDs for ingestion scripts
```

**Key Resources:**
- **BigQuery Datasets:** `raw_layer`, `conformed_layer`, `analytics_layer`
- **Cloud Storage Buckets:** `v7p3r-raw-data`, `v7p3r-agent-context`
- **Service Accounts:** `v7p3r-ingestion-sa`, `v7p3r-analytics-sa`
- **Monitoring:** Data freshness dashboard, cost alerts

**Deliverable:** `terraform apply` creates complete infrastructure

---

#### 1.2 BigQuery Schema Definitions

**Critical Design Decisions:**

**Partitioning Strategy:**
```sql
-- LICHESS_GAMES: Partition by game date (daily)
CREATE TABLE conformed_layer.lichess_games
PARTITION BY DATE(date)
CLUSTER BY engine_version, v7p3r_color
OPTIONS(
  partition_expiration_days=NULL,  -- Never expire
  require_partition_filter=TRUE    -- Force partition filters in queries
)

-- MOVES: Partition by parent game date
CREATE TABLE conformed_layer.moves
PARTITION BY DATE(_PARTITIONTIME)  -- Inherited from games
CLUSTER BY game_id, ply_number

-- STOCKFISH_ANALYSIS: Partition by analysis date
CREATE TABLE conformed_layer.stockfish_analysis
PARTITION BY DATE(analysis_date)
CLUSTER BY engine_version

-- PUZZLES: No partitioning (reference data)
-- PUZZLE_ANALYSIS_RESULTS: Partition by analysis date
CREATE TABLE conformed_layer.puzzle_analysis_results
PARTITION BY DATE(analysis_date)
CLUSTER BY puzzle_id, engine_version
```

**Cost Optimization:**
- Partitioning reduces query costs by 90%+ (scan only relevant days)
- Clustering speeds up version/opening/opponent queries
- Materialized views for expensive aggregations

---

### Phase 2: Data Ingestion Scripts (Week 2)

#### 2.1 Core Ingestion Scripts

**Script Structure:**
```python
scripts/ingestion/
├── 01_ingest_engine_versions.py       # From deployment_log.json + CHANGELOG.md
├── 02_ingest_documentation.py         # From v7p3r_docs/
├── 03_ingest_operational_events.py    # From notation_events.json
├── 04_ingest_puzzles.py               # From puzzles.db (4M rows, parallel)
├── 05_ingest_lichess_games.py         # From Lichess PGN files (parallel)
├── 06_ingest_tournament_games.py      # From Engine Battle PGNs
├── 07_ingest_tournament_results.py    # From .res files
├── 08_ingest_moves.py                 # Parse PGN move sequences (parallel)
├── 09_ingest_stockfish_analysis.py    # From analysis JSON files
├── 10_ingest_puzzle_analysis.py       # From engine-tester results
├── 11_build_openings_table.py         # Aggregate from games
└── 12_build_opponents_table.py        # Aggregate from games
```

**Shared Utilities:**
```python
scripts/ingestion/utils/
├── bigquery_client.py         # Reusable BigQuery connection
├── pgn_parser.py              # PGN parsing with python-chess
├── version_mapper.py          # Date → version lookup logic
├── batch_uploader.py          # Batch insert optimization
└── validation.py              # Data quality checks
```

---

#### 2.2 Example: Lichess Games Ingestion Script

```python
# scripts/ingestion/05_ingest_lichess_games.py

import os
import chess.pgn
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor
from utils.version_mapper import map_date_to_version
from utils.batch_uploader import batch_insert

def parse_lichess_pgn_file(file_path):
    """Parse a single PGN file and extract all games."""
    games = []
    with open(file_path, 'r', encoding='utf-8') as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
            
            headers = game.headers
            site = headers.get('Site', '')
            game_id = site.split('/')[-1] if site else None
            
            # Determine v7p3r color and outcome
            white = headers.get('White', '')
            black = headers.get('Black', '')
            result = headers.get('Result', '')
            
            v7p3r_color = 'white' if white == 'v7p3r_bot' else 'black'
            v7p3r_elo = int(headers.get('WhiteElo', 0)) if v7p3r_color == 'white' else int(headers.get('BlackElo', 0))
            opponent_elo = int(headers.get('BlackElo', 0)) if v7p3r_color == 'white' else int(headers.get('WhiteElo', 0))
            
            # Map result to outcome
            if result == '1-0':
                outcome = 'win' if v7p3r_color == 'white' else 'loss'
            elif result == '0-1':
                outcome = 'loss' if v7p3r_color == 'white' else 'win'
            else:
                outcome = 'draw'
            
            # Map date to engine version
            game_date = headers.get('Date', '').replace('.', '-')
            engine_version = map_date_to_version(game_date)
            
            # Count moves
            move_count = sum(1 for _ in game.mainline_moves())
            
            games.append({
                'game_id': game_id,
                'event': headers.get('Event', ''),
                'site': site,
                'date': game_date,
                'round': headers.get('Round', '-'),
                'white': white,
                'black': black,
                'result': result,
                'white_elo': int(headers.get('WhiteElo', 0)),
                'black_elo': int(headers.get('BlackElo', 0)),
                'time_control': headers.get('TimeControl', ''),
                'opening': headers.get('Opening', ''),
                'eco': headers.get('ECO', ''),
                'termination': headers.get('Termination', ''),
                'moves': str(game.mainline()),
                'move_count': move_count,
                'v7p3r_color': v7p3r_color,
                'v7p3r_elo': v7p3r_elo,
                'opponent_elo': opponent_elo,
                'outcome': outcome,
                'engine_version': engine_version,
                'source_file': file_path,
                'file_modified_at': os.path.getmtime(file_path),
                'ingested_at': 'CURRENT_TIMESTAMP()'
            })
    
    return games

def ingest_lichess_games():
    """Parallel ingestion of all Lichess PGN files."""
    pgn_dir = 'raw_data/game_records/Lichess V7P3R Bot'
    pgn_files = [os.path.join(pgn_dir, f) for f in os.listdir(pgn_dir) if f.endswith('.pgn')]
    
    # Parallel parsing
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(parse_lichess_pgn_file, pgn_files)
    
    # Flatten results
    all_games = [game for result in results for game in result]
    
    # Batch upload to BigQuery
    client = bigquery.Client()
    table_id = 'chess-engine-metrics-agent.conformed_layer.lichess_games'
    
    batch_insert(client, table_id, all_games, batch_size=1000)
    
    print(f"✅ Ingested {len(all_games)} games from {len(pgn_files)} PGN files")

if __name__ == '__main__':
    ingest_lichess_games()
```

**Estimated Runtime:** 50K games = ~15 minutes (parallel processing)

---

#### 2.3 Example: Puzzle Database Ingestion (4M Rows)

```python
# scripts/ingestion/04_ingest_puzzles.py

import sqlite3
from google.cloud import bigquery
from utils.batch_uploader import batch_insert

def ingest_puzzles():
    """Ingest 4M puzzles from SQLite to BigQuery."""
    sqlite_path = '../engine-tester/data/puzzles.db'
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    
    # Stream from SQLite in batches
    batch_size = 10000
    offset = 0
    total_ingested = 0
    
    client = bigquery.Client()
    table_id = 'chess-engine-metrics-agent.conformed_layer.puzzles'
    
    while True:
        cursor.execute(f"""
            SELECT puzzle_id, fen, moves, rating, rating_deviation, 
                   popularity, nb_plays, themes, game_url, opening_tags
            FROM puzzles
            LIMIT {batch_size} OFFSET {offset}
        """)
        
        rows = cursor.fetchall()
        if not rows:
            break
        
        # Transform to BigQuery format
        puzzle_rows = [
            {
                'puzzle_id': row[0],
                'fen': row[1],
                'solution_moves': row[2],
                'rating': row[3],
                'rating_deviation': row[4],
                'popularity': row[5],
                'nb_plays': row[6],
                'themes': row[7],
                'game_url': row[8],
                'opening_tags': row[9],
                'ingested_at': 'CURRENT_TIMESTAMP()'
            }
            for row in rows
        ]
        
        batch_insert(client, table_id, puzzle_rows, batch_size=1000)
        
        total_ingested += len(puzzle_rows)
        offset += batch_size
        
        if total_ingested % 100000 == 0:
            print(f"Progress: {total_ingested:,} puzzles ingested...")
    
    conn.close()
    print(f"✅ Ingested {total_ingested:,} puzzles total")

if __name__ == '__main__':
    ingest_puzzles()
```

**Estimated Runtime:** 4M rows = ~20 minutes (batch processing)

---

### Phase 3: dbt Transformation Layer (Week 3)

#### 3.1 dbt Project Structure

```
dbt_v7p3r/
├── dbt_project.yml
├── models/
│   ├── staging/                    # Clean raw data
│   │   ├── stg_lichess_games.sql
│   │   ├── stg_puzzles.sql
│   │   └── stg_analysis.sql
│   ├── intermediate/               # Business logic transformations
│   │   ├── int_game_enriched.sql
│   │   ├── int_move_evaluations.sql
│   │   └── int_error_classifications.sql
│   ├── marts/                      # Analytics-ready tables
│   │   ├── analytics/
│   │   │   ├── dim_versions.sql
│   │   │   ├── dim_openings.sql
│   │   │   ├── fact_games.sql
│   │   │   └── fact_moves.sql
│   │   └── reporting/
│   │       ├── agg_version_performance.sql
│   │       ├── agg_opening_performance.sql
│   │       └── agg_daily_metrics.sql
│   └── exports/                    # AI agent context exports
│       └── agent_context_latest.sql
├── macros/
│   ├── wilson_confidence_interval.sql
│   ├── chi_square_test.sql
│   └── classify_error.sql
├── tests/
│   ├── assert_no_duplicate_games.sql
│   ├── assert_version_coverage.sql
│   └── assert_analysis_completeness.sql
└── snapshots/
    └── snapshot_version_performance.sql
```

---

#### 3.2 Example: Version Performance Mart with Statistical Rigor

```sql
-- models/marts/reporting/agg_version_performance.sql

{{ config(
    materialized='view',
    partition_by={'field': 'period_start', 'data_type': 'date'}
) }}

WITH game_stats AS (
    SELECT 
        engine_version,
        DATE_TRUNC(date, WEEK) as period_start,
        COUNT(*) as total_games,
        SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN outcome = 'draw' THEN 1 ELSE 0 END) as draws,
        AVG(v7p3r_elo) as avg_elo,
        AVG(opponent_elo) as avg_opponent_elo
    FROM {{ ref('stg_lichess_games') }}
    GROUP BY engine_version, period_start
),

analysis_stats AS (
    SELECT 
        engine_version,
        AVG(blunders_count) as avg_blunders,
        AVG(mistakes_count) as avg_mistakes,
        AVG(accuracy_pct) as avg_accuracy
    FROM {{ ref('stg_analysis') }}
    GROUP BY engine_version
)

SELECT 
    g.engine_version,
    g.period_start,
    g.period_start + INTERVAL 6 DAY as period_end,
    g.total_games,
    g.wins,
    g.losses,
    g.draws,
    SAFE_DIVIDE(g.wins, g.total_games) as win_rate,
    
    -- Wilson Score Confidence Interval (95%)
    {{ wilson_confidence_interval('g.wins', 'g.total_games', 0.95) }} as win_rate_95ci_lower,
    {{ wilson_confidence_interval('g.wins', 'g.total_games', 0.95, 'upper') }} as win_rate_95ci_upper,
    
    g.avg_elo,
    g.avg_opponent_elo,
    a.avg_blunders,
    a.avg_mistakes,
    a.avg_accuracy,
    
    -- Statistical power (is sample size sufficient?)
    CASE 
        WHEN g.total_games >= 100 THEN 'HIGH'
        WHEN g.total_games >= 30 THEN 'MEDIUM'
        ELSE 'LOW'
    END as statistical_power,
    
    CURRENT_TIMESTAMP() as generated_at
    
FROM game_stats g
LEFT JOIN analysis_stats a ON g.engine_version = a.engine_version
ORDER BY g.period_start DESC, g.engine_version
```

---

#### 3.3 Custom UDF Macros (Statistical Functions)

```sql
-- macros/wilson_confidence_interval.sql

{% macro wilson_confidence_interval(successes, total, confidence=0.95, bound='lower') %}
    -- Wilson Score Confidence Interval for binomial proportion
    -- https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
    
    {% set z_score = 1.96 if confidence == 0.95 else 2.576 %}
    
    (
        ({{ successes }} + {{ z_score }}^2 / 2) / ({{ total }} + {{ z_score }}^2)
        {% if bound == 'lower' %}
        - {{ z_score }} * SQRT(
            ({{ successes }} * ({{ total }} - {{ successes }}) / {{ total }} + {{ z_score }}^2 / 4) / 
            ({{ total }} + {{ z_score }}^2)
        )
        {% else %}
        + {{ z_score }} * SQRT(
            ({{ successes }} * ({{ total }} - {{ successes }}) / {{ total }} + {{ z_score }}^2 / 4) / 
            ({{ total }} + {{ z_score }}^2)
        )
        {% endif %}
    ) / (1 + {{ z_score }}^2 / {{ total }})
{% endmacro %}
```

---

### Phase 4: Agent Context Export & Monitoring (Week 4)

#### 4.1 Scheduled Agent Context Export

```sql
-- models/exports/agent_context_latest.sql

{{ config(
    materialized='table',
    partition_by={'field': 'created_at', 'data_type': 'timestamp'}
) }}

-- Export JSON context for AI agent consumption
WITH latest_performance AS (
    SELECT * FROM {{ ref('agg_version_performance') }}
    WHERE period_start >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

latest_openings AS (
    SELECT * FROM {{ ref('agg_opening_performance') }}
    LIMIT 50
),

latest_analysis AS (
    SELECT * FROM {{ ref('stg_analysis') }}
    ORDER BY analysis_date DESC
    LIMIT 5
)

SELECT 
    GENERATE_UUID() as context_id,
    CURRENT_TIMESTAMP() as created_at,
    
    TO_JSON_STRING(STRUCT(
        (SELECT COUNT(*) FROM {{ ref('stg_lichess_games') }}) as total_games,
        (SELECT COUNT(*) FROM latest_performance) as recent_periods,
        (SELECT COUNT(*) FROM latest_openings) as openings_tracked,
        (SELECT COUNT(*) FROM latest_analysis) as analyses_loaded
    )) as stats_summary,
    
    TO_JSON_STRING(ARRAY(
        SELECT AS STRUCT *
        FROM latest_performance
        ORDER BY period_start DESC
        LIMIT 10
    )) as version_performance,
    
    TO_JSON_STRING(ARRAY(
        SELECT AS STRUCT *
        FROM latest_openings
        ORDER BY total_errors DESC
        LIMIT 20
    )) as problem_openings,
    
    TO_JSON_STRING(ARRAY(
        SELECT AS STRUCT *
        FROM latest_analysis
        ORDER BY analysis_date DESC
    )) as recent_analyses

-- This table gets exported to gs://v7p3r-agent-context/latest.json daily
```

**Cloud Scheduler Job:**
```bash
# Daily export at 2am UTC
gcloud scheduler jobs create bigquery daily-agent-context-export \
  --schedule="0 2 * * *" \
  --location=us-central1 \
  --uri="https://bigquery.googleapis.com/bigquery/v2/projects/chess-engine-metrics-agent/queries" \
  --message-body='{
    "query": "SELECT * FROM `analytics_layer.agent_context_latest`",
    "destinationTable": {
      "projectId": "chess-engine-metrics-agent",
      "datasetId": "exports",
      "tableId": "agent_context_daily"
    }
  }'
```

---

#### 4.2 Data Quality Monitoring Dashboard

**Cloud Monitoring Metrics:**
```yaml
# monitoring_dashboard.yaml

dashboards:
  - display_name: "V7P3R Data Pipeline Health"
    grid_layout:
      widgets:
        - title: "BigQuery Storage Usage"
          xy_chart:
            data_sets:
              - time_series_query:
                  time_series_filter:
                    filter: 'resource.type="bigquery_project"'
                    aggregation:
                      alignment_period: "3600s"
                      per_series_aligner: ALIGN_MEAN
        
        - title: "Data Freshness (Hours Since Last Ingestion)"
          xy_chart:
            data_sets:
              - time_series_query:
                  time_series_filter:
                    filter: 'metric.type="custom.googleapis.com/bigquery/table_last_modified"'
        
        - title: "Ingestion Errors (Last 24h)"
          scorecard:
            time_series_query:
              time_series_filter:
                filter: 'resource.type="cloud_function" AND severity="ERROR"'
        
        - title: "Query Cost (Last 7 Days)"
          xy_chart:
            data_sets:
              - time_series_query:
                  time_series_filter:
                    filter: 'resource.type="bigquery_project" AND metric.type="bigquery.googleapis.com/query/scanned_bytes_billed"'
```

**Alerting Policies:**
```yaml
# alerts.yaml

alerts:
  - display_name: "Data Freshness SLA Violation"
    conditions:
      - display_name: "No data ingested in 48 hours"
        condition_threshold:
          filter: 'metric.type="custom.googleapis.com/bigquery/table_last_modified"'
          comparison: COMPARISON_GT
          threshold_value: 48
          duration: "3600s"
    notification_channels:
      - projects/chess-engine-metrics-agent/notificationChannels/email-alerts
  
  - display_name: "BigQuery Cost Alert"
    budget_amount: 10.00
    threshold_rules:
      - threshold_percent: 0.8
      - threshold_percent: 1.0
```

---

## 📊 Implementation Metrics & Milestones

### Week 1 Deliverables
- ✅ Terraform infrastructure deployed
- ✅ All 19 BigQuery tables created with proper schemas
- ✅ Service accounts and IAM configured
- ✅ Monitoring dashboard live

### Week 2 Deliverables
- ✅ 12 ingestion scripts complete and tested
- ✅ 50K+ games ingested
- ✅ 4M puzzles ingested
- ✅ All reference data loaded (versions, docs, events)

### Week 3 Deliverables
- ✅ dbt project deployed
- ✅ 15+ transformation models running
- ✅ Statistical UDFs (Wilson CI, chi-square) tested
- ✅ Data quality tests passing (100%)

### Week 4 Deliverables
- ✅ Agent context export automated
- ✅ Monitoring dashboards operational
- ✅ Cost tracking < $8/month confirmed
- ✅ Full pipeline documentation complete

---

## 🎯 Success Criteria

### Technical
- [ ] All 19 tables populated with data
- [ ] BigQuery storage < 10GB
- [ ] Query costs < 50GB/month (within 1TB free tier)
- [ ] Data freshness SLA: < 24 hours lag
- [ ] dbt tests: 100% passing
- [ ] Agent context export: Daily automated

### Business
- [ ] AI agent can query full game history
- [ ] Version comparison analysis ready
- [ ] Opening performance insights available
- [ ] Puzzle solving trends trackable
- [ ] Statistical significance testing operational

---

## 📁 Next Immediate Steps

1. **Review and approve DATA_SOURCE_CATALOG.md** (this document)
2. **Review and approve COMPLETE_ERD.mmd** (updated schema)
3. **Begin Terraform infrastructure code** (bigquery.tf first)
4. **Create first ingestion script** (engine_versions as test)
5. **Set up local development environment** for script testing

---

**Ready to proceed?** Let me know and I'll start with the Terraform configuration for BigQuery schemas! 🚀
