# BigQuery Cleanup & Rebuild Plan

**Project:** chess-engine-metrics-agent  
**Date:** 2026-04-24  
**Action:** Strip to frame, rebuild 3-layer lakehouse

---

## 📊 Current State (Artifacts from Previous Work)

### Dataset: `chess_engine_data_lake` (Raw Layer - OLD)
**Tables:**
- `analysis_results` (TABLE)
- `documentation` (TABLE)
- `pgn_games` (TABLE - has schema but unknown if populated)

### Dataset: `chess_analytics` (Conformed Layer - OLD)
**Tables:**
- `ai_agent_insights` (TABLE)

**Views:**
- `development_timeline` (VIEW)
- `engine_performance` (VIEW)
- `head_to_head` (VIEW)

### Dataset: `chess_reporting` (Reporting Layer - OLD)
**Tables:**
- `daily_performance_trends` (TABLE)
- `dashboard_kpis` (TABLE)
- `engine_summary_stats` (TABLE)
- `head_to_head_matrix` (TABLE)
- `v7p3r_development_timeline` (TABLE)

---

## 🎯 New Architecture (3-Layer Lakehouse)

### Layer 1: Raw / Bronze (`raw_layer`)
**Purpose:** Landing zone for "as-is" data from GCS bucket  
**Schema:** Schema-on-read, preserve original formats  
**Implementation:** External tables pointing to Cloud Storage

```
gs://v7p3r-raw-data/
├── game_records/
│   ├── lichess_v7p3r_bot/*.pgn
│   └── engine_battle_*/*.pgn, *.res
├── analysis_results/*.json
├── pgn_training_data/
│   ├── lichess_db_puzzle.csv
│   └── *.pgn (opening theory)
├── v7p3r_docs/*.md
└── notation_events.json
```

**External Tables (Auto-detected from GCS):**
- `raw_pgn_files` - External table over *.pgn (JSON/STRING columns)
- `raw_analysis_json` - External table over *.json
- `raw_puzzle_csv` - External table over lichess_db_puzzle.csv
- `raw_documentation` - External table over *.md
- `raw_events` - External table over notation_events.json

### Layer 2: Conformed / Silver (`conformed_layer`)
**Purpose:** Cleaned, deduplicated, aligned source of truth  
**Schema:** Strict, holistic, version-controlled  
**Implementation:** 15 BigQuery tables (from RAW_DATA_INVENTORY.md)

**Core Game Data:**
1. `lichess_games` - 50K+ games (partitioned by date)
2. `moves` - 2.5M moves (partitioned, clustered by game_id)
3. `stockfish_analysis` - Analysis results
4. `puzzle_analysis_results` - Puzzle test results
5. `puzzles` - 4M puzzles (reference data)

**Reference Data:**
6. `engine_versions` - Deployment history from CHANGELOG
7. `operational_events` - Non-code events affecting metrics
8. `documentation` - 173 markdown files

**New Discoveries:**
9. `opening_theory` - 500K positions from theory PGNs
10. `engine_battle_tournaments` - Tournament results from .res files

**Aggregated Data:**
11. `openings` - Opening performance (view)
12. `opponents` - Opponent stats (view)
13. `game_summaries` - Period summaries (materialized)
14. `error_patterns` - Blunder/mistake patterns
15. `ai_agent_context` - AI agent export (materialized view)

### Layer 3: Reporting / Gold (`reporting_layer`)
**Purpose:** Aggregated, optimized for specific consumption  
**Schema:** Denormalized, pre-calculated, consumer-specific  
**Implementation:** Materialized views and specialized tables

**Tables/Views:**
- `version_performance_weekly` - Pre-calculated weekly stats
- `opening_heatmap` - Win rate by opening for dashboards
- `agent_context_latest` - Flattened context for AI agent
- `elo_trajectory` - ELO changes over time
- `tournament_summary` - Tournament standings
- `blunder_hotspots` - Error pattern analysis

---

## 🗑️ Cleanup Script

### Step 1: Delete All Old Tables/Views

```bash
# Delete chess_engine_data_lake tables
bq rm -f -t chess-engine-metrics-agent:chess_engine_data_lake.analysis_results
bq rm -f -t chess-engine-metrics-agent:chess_engine_data_lake.documentation
bq rm -f -t chess-engine-metrics-agent:chess_engine_data_lake.pgn_games

# Delete chess_analytics views first (views before tables)
bq rm -f -t chess-engine-metrics-agent:chess_analytics.development_timeline
bq rm -f -t chess-engine-metrics-agent:chess_analytics.engine_performance
bq rm -f -t chess-engine-metrics-agent:chess_analytics.head_to_head

# Delete chess_analytics table
bq rm -f -t chess-engine-metrics-agent:chess_analytics.ai_agent_insights

# Delete chess_reporting tables
bq rm -f -t chess-engine-metrics-agent:chess_reporting.daily_performance_trends
bq rm -f -t chess-engine-metrics-agent:chess_reporting.dashboard_kpis
bq rm -f -t chess-engine-metrics-agent:chess_reporting.engine_summary_stats
bq rm -f -t chess-engine-metrics-agent:chess_reporting.head_to_head_matrix
bq rm -f -t chess-engine-metrics-agent:chess_reporting.v7p3r_development_timeline
```

### Step 2: Rename Datasets (or Create New Ones)

**Option A: Rename existing datasets**
```bash
# Cannot rename datasets directly in BigQuery
# Must create new and copy (but we're starting fresh, so just create new)
```

**Option B: Create new datasets with correct names**
```bash
# Create new datasets
bq mk --dataset \
  --description="Raw layer - External tables pointing to Cloud Storage" \
  --location=us-central1 \
  chess-engine-metrics-agent:raw_layer

bq mk --dataset \
  --description="Conformed layer - Cleaned, deduplicated source of truth" \
  --location=us-central1 \
  chess-engine-metrics-agent:conformed_layer

bq mk --dataset \
  --description="Reporting layer - Aggregated, optimized for consumption" \
  --location=us-central1 \
  chess-engine-metrics-agent:reporting_layer
```

### Step 3: Delete Old Datasets (After New Ones Created)

```bash
# Delete old datasets (only after confirming new ones are set up)
bq rm -r -f -d chess-engine-metrics-agent:chess_engine_data_lake
bq rm -r -f -d chess-engine-metrics-agent:chess_analytics
bq rm -r -f -d chess-engine-metrics-agent:chess_reporting
```

---

## 🏗️ Rebuild Plan

### Phase 1: Set Up Cloud Storage Bucket

```bash
# Create bucket for raw data (if not exists)
gsutil mb -l us-central1 -c STANDARD gs://v7p3r-raw-data

# Upload raw_data from local to GCS
gsutil -m rsync -r "e:\Programming Stuff\Chess Engines\Chess Engine Playground\engine-metrics\raw_data\" gs://v7p3r-raw-data/

# Set lifecycle policy (optional - for cost optimization)
gsutil lifecycle set lifecycle-policy.json gs://v7p3r-raw-data/
```

**Lifecycle Policy (lifecycle-policy.json):**
```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 90}
      }
    ]
  }
}
```

### Phase 2: Create Raw Layer (External Tables)

```sql
-- External table for PGN files
CREATE OR REPLACE EXTERNAL TABLE raw_layer.pgn_files
OPTIONS (
  format = 'CSV',
  uris = ['gs://v7p3r-raw-data/game_records/*/*.pgn'],
  skip_leading_rows = 0,
  max_bad_records = 1000,
  field_delimiter = '\n',
  quote = ''
);

-- External table for analysis JSON
CREATE OR REPLACE EXTERNAL TABLE raw_layer.analysis_json
OPTIONS (
  format = 'NEWLINE_DELIMITED_JSON',
  uris = ['gs://v7p3r-raw-data/analysis_results/*.json'],
  max_bad_records = 100
);

-- External table for puzzle CSV
CREATE OR REPLACE EXTERNAL TABLE raw_layer.puzzles_csv (
  PuzzleId STRING,
  FEN STRING,
  Moves STRING,
  Rating INT64,
  RatingDeviation INT64,
  Popularity INT64,
  NbPlays INT64,
  Themes STRING,
  GameUrl STRING,
  OpeningTags STRING
)
OPTIONS (
  format = 'CSV',
  uris = ['gs://v7p3r-raw-data/pgn_training_data/lichess_db_puzzle.csv'],
  skip_leading_rows = 1
);

-- External table for documentation
CREATE OR REPLACE EXTERNAL TABLE raw_layer.documentation_files
OPTIONS (
  format = 'CSV',
  uris = ['gs://v7p3r-raw-data/v7p3r_docs/*.md'],
  skip_leading_rows = 0,
  max_bad_records = 100,
  field_delimiter = '\n',
  quote = ''
);
```

### Phase 3: Create Conformed Layer (15 Tables)

**Use Terraform for schema definitions** (see next section)

### Phase 4: Create Reporting Layer (Materialized Views)

**Defined in dbt project** (see IMPLEMENTATION_ROADMAP.md)

---

## 📋 Execution Order

1. ✅ **Review this cleanup plan** - Confirm approach
2. ⬜ **Backup check** - Verify old data is not needed (likely all obsolete)
3. ⬜ **Run cleanup script** - Delete all old tables/views/datasets
4. ⬜ **Upload raw_data to GCS** - `gsutil rsync` local → bucket
5. ⬜ **Create new datasets** - raw_layer, conformed_layer, reporting_layer
6. ⬜ **Create external tables** - Point to GCS for raw layer
7. ⬜ **Deploy Terraform** - Create conformed_layer schemas (15 tables)
8. ⬜ **Run ingestion scripts** - Load data from raw → conformed
9. ⬜ **Deploy dbt** - Build reporting_layer views

---

## 🔧 Complete Cleanup Script (PowerShell)

```powershell
# cleanup_bigquery.ps1

Write-Host "Starting BigQuery cleanup..." -ForegroundColor Cyan

# Step 1: Delete all tables in chess_engine_data_lake
Write-Host "`n[1/4] Deleting chess_engine_data_lake tables..." -ForegroundColor Yellow
bq rm -f -t chess-engine-metrics-agent:chess_engine_data_lake.analysis_results
bq rm -f -t chess-engine-metrics-agent:chess_engine_data_lake.documentation
bq rm -f -t chess-engine-metrics-agent:chess_engine_data_lake.pgn_games

# Step 2: Delete all views/tables in chess_analytics
Write-Host "`n[2/4] Deleting chess_analytics views and tables..." -ForegroundColor Yellow
bq rm -f -t chess-engine-metrics-agent:chess_analytics.development_timeline
bq rm -f -t chess-engine-metrics-agent:chess_analytics.engine_performance
bq rm -f -t chess-engine-metrics-agent:chess_analytics.head_to_head
bq rm -f -t chess-engine-metrics-agent:chess_analytics.ai_agent_insights

# Step 3: Delete all tables in chess_reporting
Write-Host "`n[3/4] Deleting chess_reporting tables..." -ForegroundColor Yellow
bq rm -f -t chess-engine-metrics-agent:chess_reporting.daily_performance_trends
bq rm -f -t chess-engine-metrics-agent:chess_reporting.dashboard_kpis
bq rm -f -t chess-engine-metrics-agent:chess_reporting.engine_summary_stats
bq rm -f -t chess-engine-metrics-agent:chess_reporting.head_to_head_matrix
bq rm -f -t chess-engine-metrics-agent:chess_reporting.v7p3r_development_timeline

# Step 4: Delete old datasets
Write-Host "`n[4/4] Deleting old datasets..." -ForegroundColor Yellow
bq rm -r -f -d chess-engine-metrics-agent:chess_engine_data_lake
bq rm -r -f -d chess-engine-metrics-agent:chess_analytics
bq rm -r -f -d chess-engine-metrics-agent:chess_reporting

Write-Host "`n✅ Cleanup complete! BigQuery stripped to frame." -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Run setup_new_architecture.ps1 to create new datasets"
Write-Host "  2. Upload raw_data to GCS bucket"
Write-Host "  3. Create external tables for raw layer"
Write-Host "  4. Deploy Terraform for conformed layer"
```

## 🚀 Setup New Architecture Script (PowerShell)

```powershell
# setup_new_architecture.ps1

Write-Host "Setting up new 3-layer lakehouse architecture..." -ForegroundColor Cyan

# Create new datasets
Write-Host "`n[1/3] Creating raw_layer dataset..." -ForegroundColor Yellow
bq mk --dataset `
  --description="Raw layer - External tables pointing to Cloud Storage" `
  --location=us-central1 `
  chess-engine-metrics-agent:raw_layer

Write-Host "`n[2/3] Creating conformed_layer dataset..." -ForegroundColor Yellow
bq mk --dataset `
  --description="Conformed layer - Cleaned, deduplicated source of truth" `
  --location=us-central1 `
  chess-engine-metrics-agent:conformed_layer

Write-Host "`n[3/3] Creating reporting_layer dataset..." -ForegroundColor Yellow
bq mk --dataset `
  --description="Reporting layer - Aggregated, optimized for consumption" `
  --location=us-central1 `
  chess-engine-metrics-agent:reporting_layer

Write-Host "`n✅ New datasets created!" -ForegroundColor Green
Write-Host "`nDatasets:" -ForegroundColor Cyan
bq ls --project_id=chess-engine-metrics-agent

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Upload raw_data to gs://v7p3r-raw-data/"
Write-Host "  2. Create external tables in raw_layer"
Write-Host "  3. Deploy Terraform for conformed_layer schemas"
```

---

## ✅ Validation Checklist

After cleanup and rebuild:

- [ ] Old datasets deleted (`chess_engine_data_lake`, `chess_analytics`, `chess_reporting`)
- [ ] New datasets created (`raw_layer`, `conformed_layer`, `reporting_layer`)
- [ ] Raw data uploaded to GCS bucket (`gs://v7p3r-raw-data/`)
- [ ] External tables created in `raw_layer`
- [ ] Conformed layer schemas deployed (15 tables)
- [ ] Ingestion scripts ready
- [ ] dbt project configured for reporting layer

---

## 📊 Expected Final State

```
BigQuery Project: chess-engine-metrics-agent
├── raw_layer (4 external tables)
│   ├── pgn_files (→ GCS: *.pgn)
│   ├── analysis_json (→ GCS: *.json)
│   ├── puzzles_csv (→ GCS: lichess_db_puzzle.csv)
│   └── documentation_files (→ GCS: *.md)
│
├── conformed_layer (15 tables)
│   ├── lichess_games (50K rows, partitioned)
│   ├── moves (2.5M rows, partitioned)
│   ├── stockfish_analysis
│   ├── puzzle_analysis_results
│   ├── puzzles (4M rows)
│   ├── engine_versions
│   ├── operational_events
│   ├── documentation
│   ├── opening_theory (500K rows)
│   ├── engine_battle_tournaments
│   ├── openings (view)
│   ├── opponents (view)
│   ├── game_summaries (materialized)
│   ├── error_patterns
│   └── ai_agent_context (materialized)
│
└── reporting_layer (6 materialized views)
    ├── version_performance_weekly
    ├── opening_heatmap
    ├── agent_context_latest
    ├── elo_trajectory
    ├── tournament_summary
    └── blunder_hotspots
```

**Storage:** ~5 GB conformed + 2.58 GB raw (external)  
**Monthly Cost:** ~$5 (mostly Vertex AI, BigQuery within free tier)  
**Query Performance:** 90% faster with partitioning/clustering

---

## 🎯 Ready to Execute?

Review this plan and confirm:
1. Safe to delete all old datasets? (They appear to be outdated/test data)
2. Preferred approach: Run scripts or manual cleanup?
3. GCS bucket name: `gs://v7p3r-raw-data/` OK?

Then we'll execute the cleanup and start building! 🚀
