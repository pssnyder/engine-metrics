# BigQuery 3-Layer Lakehouse - Quick Start Guide

**Project:** chess-engine-metrics-agent  
**Date:** 2026-04-24  
**Architecture:** Raw (Bronze) → Conformed (Silver) → Reporting (Gold)

---

## 🎯 What We're Building

### Current State (OLD)
- ❌ Scattered datasets: `chess_engine_data_lake`, `chess_analytics`, `chess_reporting`
- ❌ Mixed schemas from previous experiments
- ❌ No clear separation of raw vs. conformed data

### Target State (NEW)
- ✅ `raw_layer` - External tables pointing to GCS (schema-on-read)
- ✅ `conformed_layer` - 15 tables with strict schemas (source of truth)
- ✅ `reporting_layer` - Materialized views for analytics

---

## 📋 Execution Steps

### Step 1: Cleanup Old Architecture

**Script:** `scripts\cleanup_bigquery.ps1`

**What it does:**
- Deletes all tables/views in `chess_engine_data_lake`, `chess_analytics`, `chess_reporting`
- Removes the old datasets completely
- Clears BigQuery to a fresh state

**Run:**
```powershell
cd "e:\Programming Stuff\Chess Engines\Chess Engine Playground\engine-metrics"
.\scripts\cleanup_bigquery.ps1
```

**Confirmation required:** Type `yes` when prompted

**Expected output:**
```
✅ Cleanup complete! BigQuery stripped to frame.
```

---

### Step 2: Create New Datasets

**Script:** `scripts\setup_new_architecture.ps1`

**What it does:**
- Creates `raw_layer` dataset (for external tables)
- Creates `conformed_layer` dataset (for cleaned data)
- Creates `reporting_layer` dataset (for analytics)

**Run:**
```powershell
.\scripts\setup_new_architecture.ps1
```

**Expected output:**
```
✅ New architecture datasets created!

Datasets:
  raw_layer
  conformed_layer
  reporting_layer
```

---

### Step 3: Upload Raw Data to Cloud Storage

**Script:** `scripts\upload_raw_data.ps1`

**What it does:**
- Creates `gs://v7p3r-raw-data/` bucket (if not exists)
- Uploads 2.58 GB from local `raw_data/` to GCS
- Uses `gsutil rsync` (only uploads new/changed files)

**Run:**
```powershell
.\scripts\upload_raw_data.ps1
```

**Expected duration:** 5-10 minutes (2.58 GB upload)

**Expected output:**
```
✅ Upload complete!

Bucket contents:
  2.4 GB  gs://v7p3r-raw-data/pgn_training_data
  139 MB  gs://v7p3r-raw-data/game_records
  94 MB   gs://v7p3r-raw-data/analysis_results
  1.6 MB  gs://v7p3r-raw-data/v7p3r_docs
```

---

### Step 4: Create External Tables (Raw Layer)

**Script:** `scripts\create_external_tables.ps1`

**What it does:**
- Creates 5 external tables in `raw_layer`:
  1. `raw_puzzles_csv` - 4M puzzles from CSV (861 MB)
  2. `raw_analysis_json` - Analysis results (auto-detected schema)
  3. `raw_pgn_lichess` - PGN game files (schema-on-read)
  4. `raw_notation_events` - Operational events JSON
  5. `raw_documentation` - Markdown files (173 docs)

**Run:**
```powershell
.\scripts\create_external_tables.ps1
```

**Expected output:**
```
✅ External tables ready!

Tables in raw_layer:
  raw_puzzles_csv
  raw_analysis_json
  raw_pgn_lichess
  raw_notation_events
  raw_documentation
```

**Test query:**
```sql
-- Query 4M puzzles directly from GCS
SELECT PuzzleId, FEN, Rating, Themes
FROM `chess-engine-metrics-agent.raw_layer.raw_puzzles_csv`
WHERE Rating >= 2000
LIMIT 10;
```

---

## ✅ Verification Checklist

After running all 4 scripts, verify:

```powershell
# Check datasets exist
bq ls --project_id=chess-engine-metrics-agent

# Should show:
#   raw_layer
#   conformed_layer
#   reporting_layer

# Check external tables in raw_layer
bq ls chess-engine-metrics-agent:raw_layer

# Should show 5 tables:
#   raw_puzzles_csv
#   raw_analysis_json
#   raw_pgn_lichess
#   raw_notation_events
#   raw_documentation

# Check GCS bucket contents
gsutil ls -lh gs://v7p3r-raw-data/

# Should show:
#   analysis_results/ (94 MB)
#   game_records/ (139 MB)
#   pgn_training_data/ (2.4 GB)
#   v7p3r_docs/ (1.6 MB)
#   notation_events.json
```

---

## 🎯 What's Next?

### Phase 1: Conformed Layer (Week 1-2)

**Deploy Terraform Infrastructure:**
```powershell
cd terraform
terraform init
terraform plan
terraform apply
```

**Creates 15 tables in conformed_layer:**
1. `lichess_games` - 50K+ games (partitioned by date)
2. `moves` - 2.5M moves (partitioned, clustered)
3. `stockfish_analysis` - Analysis results
4. `puzzle_analysis_results` - Puzzle test results
5. `puzzles` - 4M puzzles (reference data)
6. `engine_versions` - Version history
7. `operational_events` - Events log
8. `documentation` - 173 docs
9. `opening_theory` - 500K positions
10. `engine_battle_tournaments` - Tournament results
11. `openings` - Opening stats (view)
12. `opponents` - Opponent stats (view)
13. `game_summaries` - Period summaries
14. `error_patterns` - Blunder analysis
15. `ai_agent_context` - AI export (materialized view)

### Phase 2: Ingestion Scripts (Week 2-3)

**Run ingestion to populate conformed_layer:**
```powershell
# Ingest reference data first
python scripts/ingestion/01_ingest_engine_versions.py
python scripts/ingestion/02_ingest_operational_events.py
python scripts/ingestion/03_ingest_documentation.py

# Ingest puzzles (4M rows, ~25 min)
python scripts/ingestion/04_ingest_puzzles.py

# Ingest games and moves (50K games, ~20 min)
python scripts/ingestion/05_ingest_lichess_games.py
python scripts/ingestion/06_ingest_moves.py

# Ingest analysis
python scripts/ingestion/07_ingest_stockfish_analysis.py
python scripts/ingestion/08_ingest_puzzle_tests.py

# Run all at once (parallel processing)
python scripts/ingestion/run_all_ingestion.py
```

### Phase 3: Reporting Layer (Week 3-4)

**Deploy dbt transformations:**
```powershell
cd dbt_v7p3r
dbt deps
dbt run
dbt test
```

**Creates materialized views in reporting_layer:**
- `version_performance_weekly` - Weekly stats by version
- `opening_heatmap` - Win rates by opening
- `agent_context_latest` - Flattened for AI agent
- `elo_trajectory` - ELO over time
- `tournament_summary` - Tournament standings
- `blunder_hotspots` - Error pattern heatmap

---

## 🚨 Troubleshooting

### Issue: "Bucket already exists"
**Solution:** Bucket exists from previous work. Script will skip creation and proceed with upload.

### Issue: "Permission denied" on GCS upload
**Solution:**
```powershell
# Authenticate with application default credentials
gcloud auth application-default login

# Or set project explicitly
gcloud config set project chess-engine-metrics-agent
```

### Issue: External table shows 0 rows
**Solution:** Check if files uploaded correctly:
```powershell
gsutil ls -lh gs://v7p3r-raw-data/pgn_training_data/

# Should show lichess_db_puzzle.csv (861 MB)
```

### Issue: "Dataset not found" error
**Solution:** Run setup script again:
```powershell
.\scripts\setup_new_architecture.ps1
```

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloud Storage Bucket                     │
│                  gs://v7p3r-raw-data/                       │
│  ┌───────────────┬──────────────┬─────────────┬──────────┐ │
│  │ game_records/ │ analysis_    │ pgn_training│ v7p3r_   │ │
│  │   (139 MB)    │ results/     │ _data/      │ docs/    │ │
│  │               │   (94 MB)    │  (2.4 GB)   │ (1.6 MB) │ │
│  └───────┬───────┴──────┬───────┴──────┬──────┴────┬─────┘ │
└──────────┼──────────────┼──────────────┼───────────┼───────┘
           │              │              │           │
           │   External Tables (Schema-on-Read)      │
           ▼              ▼              ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│               BigQuery - raw_layer (Bronze)                 │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐ │
│  │raw_pgn_      │raw_analysis_ │raw_puzzles_  │raw_      │ │
│  │lichess       │json          │csv           │notation_ │ │
│  │              │              │(4M rows)     │events    │ │
│  └──────┬───────┴──────┬───────┴──────┬───────┴────┬─────┘ │
└─────────┼──────────────┼──────────────┼────────────┼───────┘
          │              │              │            │
          │   Ingestion Scripts (Python + python-chess)
          ▼              ▼              ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│          BigQuery - conformed_layer (Silver)                │
│         Cleaned, Deduplicated, Aligned Tables               │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐ │
│  │lichess_games │moves         │stockfish_    │puzzles   │ │
│  │(50K rows)    │(2.5M rows)   │analysis      │(4M rows) │ │
│  │PARTITIONED   │PARTITIONED   │              │          │ │
│  │BY date       │BY game_id    │              │          │ │
│  └──────┬───────┴──────┬───────┴──────┬───────┴────┬─────┘ │
│         │              │              │            │        │
│  ┌──────┴────┬─────────┴────┬─────────┴────┬───────┴─────┐ │
│  │engine_    │operational_  │opening_      │error_       │ │
│  │versions   │events        │theory        │patterns     │ │
│  │           │              │(500K rows)   │             │ │
│  └───────────┴──────────────┴──────────────┴─────────────┘ │
└─────────────────────────────────────────────────────────────┘
           │              │              │            │
           │   dbt Transformations (SQL)             │
           ▼              ▼              ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│          BigQuery - reporting_layer (Gold)                  │
│      Aggregated, Optimized for Specific Consumers           │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐ │
│  │version_      │opening_      │agent_context_│elo_      │ │
│  │performance_  │heatmap       │latest        │trajectory│ │
│  │weekly        │(materialized)│(materialized)│          │ │
│  │(materialized)│              │              │          │ │
│  └──────────────┴──────────────┴──────────────┴──────────┘ │
│                                                             │
│  Consumer 1: AI Agent (reads agent_context_latest)         │
│  Consumer 2: Dashboard (reads opening_heatmap)             │
│  Consumer 3: Reports (reads version_performance_weekly)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 💰 Cost Estimate

| Component | Usage | Cost |
|---|---|---|
| **Cloud Storage** | 2.58 GB | $0.05/month (within 5GB free tier = $0) |
| **BigQuery Storage** | 5 GB conformed + 2 GB reporting | $0.14/month (within 10GB free tier = $0) |
| **BigQuery Queries** | 50 GB/month scanned | $0.25/month (within 1TB free tier = $0) |
| **Vertex AI (Gemini)** | 10K requests/month | ~$5/month |
| **TOTAL** | | **~$5/month** |

---

## 🎉 Success Criteria

After completing all setup:

- [ ] Old datasets deleted (`chess_engine_data_lake`, `chess_analytics`, `chess_reporting`)
- [ ] New datasets created (`raw_layer`, `conformed_layer`, `reporting_layer`)
- [ ] Raw data uploaded to GCS (2.58 GB)
- [ ] External tables created (5 tables in raw_layer)
- [ ] Can query 4M puzzles directly from GCS
- [ ] Ready for Terraform deployment (conformed_layer schemas)
- [ ] Ready for ingestion scripts (raw → conformed)
- [ ] Ready for dbt deployment (conformed → reporting)

---

## 🚀 Ready to Execute?

Run the scripts in order:

```powershell
# 1. Clean up old architecture
.\scripts\cleanup_bigquery.ps1

# 2. Create new datasets
.\scripts\setup_new_architecture.ps1

# 3. Upload raw data to GCS (5-10 min)
.\scripts\upload_raw_data.ps1

# 4. Create external tables
.\scripts\create_external_tables.ps1
```

**Then proceed to Terraform and ingestion development!** 🎯
