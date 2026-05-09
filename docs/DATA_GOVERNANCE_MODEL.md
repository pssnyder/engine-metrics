# V7P3R Analytics Data Governance Model

**Version:** 1.0  
**Date:** 2026-04-30  
**Status:** Active

---

## Executive Summary

This document defines the data governance model for the V7P3R Analytics platform, establishing rules for data flow automation, quality standards, and source data contracts across the 3-layer lakehouse architecture (Raw → Conformed → Reporting).

**Key Principles:**
- **Conformed Layer = Source of Truth** - All analytics derive from conformed layer
- **Raw → Conformed: AUTOMATED** - Triggered by file uploads, validated by contracts
- **Conformed → Reporting: MANUAL** - ETL created per analytical question
- **Append-Only Conformed Layer** - Historical records never updated, only appended
- **Idempotent Ingestion** - Re-running ingestion produces same result

---

## 1. Three-Layer Architecture

### 1.1 Raw Layer (Bronze)

**Purpose:** Landing zone for unprocessed source data  
**Location:** GCS bucket `gs://v7p3r-raw-data/`  
**Data Types:**
- PGN game files (`v7p3r_docs/`, `game_records/`)
- JSON analysis results (`analysis_results/`)
- Engine documentation (`v7p3r_docs/CHANGELOG.md`, version files)
- Notation events (`notation_events.json`)

**Data Lifecycle:**
- **Retention:** Indefinite (historical archive)
- **Access Pattern:** Write-once, read-rarely (only during ingestion)
- **Validation:** None (accept all uploads, validate during ingestion)

### 1.2 Conformed Layer (Silver)

**Purpose:** Cleaned, validated, structured source of truth  
**Location:** BigQuery dataset `chess-engine-metrics-agent.conformed_layer`  
**Current Tables:** 8 (documentation, engine_versions, operational_events, analysis_results, game_records, game_data, game_summary, moves)

**Data Lifecycle:**
- **Retention:** Indefinite (permanent record)
- **Access Pattern:** High-frequency reads, append-only writes
- **Validation:** Enforced via source data contracts (see Section 3)

**Quality Standards:**
- Primary keys enforced (game_id, version_number, etc.)
- Foreign keys validated before insertion
- Required fields must not be NULL
- Date/time fields properly typed (DATE, TIME, TIMESTAMP)
- ELO values within reasonable range (500-3000)

### 1.3 Reporting Layer (Gold)

**Purpose:** Pre-aggregated metrics for analytics and dashboards  
**Location:** BigQuery dataset `chess-engine-metrics-agent.reporting_layer`  
**Current Tables:** 7 Tier 1 KPI tables (version_performance_summary, opponent_strength_performance, opening_performance, time_control_performance, temporal_trends, castling_analysis, queen_trade_analysis)

**Data Lifecycle:**
- **Retention:** 90 days (can be rebuilt from conformed layer)
- **Access Pattern:** High-frequency reads, scheduled batch writes
- **Refresh Cadence:** Daily (Tier 1), on-demand (Tier 2)

**Derivation Rules:**
- All metrics calculated from conformed layer only
- No direct ingestion from raw layer
- Reporting tables can be dropped and rebuilt without data loss
- If reporting conflicts with conformed, conformed wins

---

## 2. Data Flow Automation

### 2.1 Raw → Conformed Flow (AUTOMATED)

**Trigger:** GCS file upload event  
**Workflow:**
1. File uploaded to `gs://v7p3r-raw-data/` subfolder
2. Cloud Function triggered by upload event
3. Function validates file against source data contract
4. If valid: Run ingestion script, append to conformed layer table
5. If invalid: Log error, move file to `gs://v7p3r-raw-data/invalid/`
6. Update `conformed_layer.operational_events` with ingestion status

**Automation Status:**
- **Current:** Manual execution via command-line scripts
- **Target:** Fully automated via Cloud Functions + GCS triggers
- **Priority:** High (Phase 4 implementation)

**Implemented Ingestion Scripts:**
- `scripts/ingestion/01_ingest_documentation.py` - Documentation files
- `scripts/ingestion/02_ingest_engine_versions.py` - CHANGELOG parsing
- `scripts/ingestion/03_ingest_operational_events.py` - Event logs
- `scripts/ingestion/04_ingest_analysis_results.py` - JSON analysis files
- `scripts/ingestion/05_ingest_game_records.py` - PGN game files
- `scripts/ingestion/06_ingest_game_data.py` - CSV game metadata
- `scripts/ingestion/07_ingest_game_summary.py` - CSV game summaries
- `scripts/ingestion/08_ingest_moves.py` - CSV move-level data

### 2.2 Conformed → Reporting Flow (MANUAL)

**Trigger:** New analytical question asked  
**Workflow:**
1. User asks analytical question (e.g., "What is V7P3R's win rate vs 2000+ ELO opponents?")
2. Check if existing reporting table answers question
3. If no: Design new reporting table schema
4. Create Terraform schema file (`terraform/reporting_*.tf`)
5. Deploy table: `terraform apply`
6. Create ETL script (`scripts/reporting_etl/*.py`)
7. Execute ETL to populate table
8. Schedule daily refresh (if Tier 1) or on-demand (if Tier 2)
9. Document in `docs/REPORTING_LAYER_DATA_DICTIONARY.md`

**Design Principle:**
- Avoid over-engineering unused metrics
- Purpose-built ETL for each use case
- Optimize per question (some real-time, some batch)

**ETL Naming Convention:**
- Pattern: `{sequence}_{action}_{entity}.py`
- Sequence 01-10: Tier 1 reporting tables
- Sequence 11-20: Tier 2 reporting tables
- Sequence 21+: Custom one-off analyses

**Implemented ETL Scripts:**
- *None yet (Phase 3 implementation)*

---

## 3. Source Data Contracts

### 3.1 Contract Purpose

**Definition:** A source data contract defines the expected schema, validation rules, and allowed expansions for a raw data source.

**Benefits:**
- Prevent breaking changes to ingestion pipelines
- Enable schema evolution without code changes
- Provide clear documentation for data producers
- Automated validation during ingestion

### 3.2 Contract Components

Each contract document must specify:
1. **Required Fields** - Must always be present (ingestion fails if missing)
2. **Optional Fields** - Nice-to-have, NULL if absent
3. **Field Types** - Data type and format (STRING, INTEGER, DATE, etc.)
4. **Validation Rules** - Constraints (ranges, patterns, foreign keys)
5. **Expansion Rules** - How new fields can be added without breaking ingestion
6. **Version History** - Changes to contract over time

### 3.3 Active Contracts

**Documented Contracts:**
1. **PGN Game Source Contract** - `contracts/pgn_game_source_contract.md`
   - Governs: PGN game files uploaded to `game_records/`
   - Tables: `conformed_layer.game_records`
   
2. **JSON Analysis Source Contract** - `contracts/json_analysis_source_contract.md`
   - Governs: Stockfish analysis JSON files
   - Tables: `conformed_layer.analysis_results` (future)
   
3. **CHANGELOG Version Source Contract** - `contracts/changelog_version_source_contract.md`
   - Governs: CHANGELOG.md version mapping
   - Tables: `conformed_layer.engine_versions`

### 3.4 Contract Enforcement

**Validation Process:**
1. Ingestion script reads source data contract
2. Validates required fields present
3. Checks data types match contract
4. Runs validation rules (ranges, patterns)
5. If validation fails: Reject file, log error, alert user
6. If validation passes: Proceed with ingestion

**Implementation:**
- Contract files stored in `contracts/` directory (Markdown format)
- Validation logic in ingestion scripts (`scripts/ingestion/`)
- Future: Automated validation via Cloud Functions

---

## 4. Data Quality Standards

### 4.1 Conformed Layer Quality Gates

**All ingestion scripts must enforce:**

**Primary Keys:**
- Every table has a primary key (game_id, version_number, etc.)
- Primary keys must be UNIQUE and NOT NULL
- Duplicate primary keys rejected during ingestion

**Foreign Keys:**
- Foreign key references validated before insertion
- Example: `game_data.engine_version` must exist in `engine_versions.version_number`
- Validation can be sampled (1000 rows) for performance on large datasets

**Required Fields:**
- Fields marked `mode = "REQUIRED"` in schema must not be NULL
- Ingestion fails if required field missing or NULL

**Data Types:**
- Date fields: DATE type (YYYY-MM-DD)
- Time fields: TIME type (HH:MM:SS)
- Timestamp fields: TIMESTAMP type (ISO 8601 with timezone)
- Integer fields: INT64 type
- Float fields: FLOAT64 type

**Value Ranges:**
- ELO ratings: 500-3000 (human-reachable range)
- Move counts: 1-500 (reasonable game length)
- Material balance: -50 to +50 (centipawns)

### 4.2 Reporting Layer Quality Gates

**All ETL scripts must ensure:**

**Aggregation Correctness:**
- Sum of wins + losses + draws = total_games
- Win rate = wins / total_games (0.0 to 1.0 range)
- Percentages stored as decimals (0.45 not 45%)

**Temporal Consistency:**
- time_period_start ≤ time_period_end
- Date ranges do not overlap for same dimension

**Non-Negative Counts:**
- total_games, wins, losses, draws ≥ 0
- Negative counts indicate ETL bug

---

## 5. Schema Evolution

### 5.1 Adding New Fields to Conformed Layer

**Backward-Compatible Changes (ALLOWED):**
- Adding new NULLABLE fields
- Adding new optional PGN headers (handled dynamically)
- Expanding enum values (e.g., new termination types)

**Breaking Changes (REQUIRES CONTRACT UPDATE):**
- Removing existing fields
- Changing field data types
- Making NULLABLE field REQUIRED
- Renaming fields

**Procedure:**
1. Update source data contract document
2. Increment contract version number
3. Update Terraform schema with new fields
4. Run `terraform apply` to add columns
5. Update ingestion script to handle new fields
6. Re-ingest historical data if needed

### 5.2 Adding New Reporting Tables

**Procedure:**
1. Document analytical question in requirements
2. Design table schema (see `docs/REPORTING_LAYER_REQUIREMENTS.md`)
3. Create Terraform schema file (`terraform/reporting_*.tf`)
4. Deploy table: `terraform apply`
5. Create ETL script (`scripts/reporting_etl/*.py`)
6. Execute ETL to populate table
7. Schedule refresh (daily or on-demand)
8. Update `docs/REPORTING_LAYER_DATA_DICTIONARY.md`

---

## 6. Error Handling & Monitoring

### 6.1 Ingestion Error Handling

**File-Level Errors:**
- Contract validation failure → Move to `invalid/` folder, log error
- Parsing error (malformed PGN, invalid JSON) → Log error, skip file
- Foreign key violation → Log error, skip file or row
- Duplicate primary key → Skip duplicate row, log warning

**Recovery:**
- All errors logged to `conformed_layer.operational_events` table
- Invalid files kept in `gs://v7p3r-raw-data/invalid/` for manual review
- Re-run ingestion after fixing source data

### 6.2 ETL Error Handling

**Aggregation Errors:**
- NULL division (0 games in category) → Skip category or use NULL
- Data type mismatch → Log error, fail ETL run
- Foreign key violation → Log error, fail ETL run

**Recovery:**
- All ETL runs logged to `reporting_layer.etl_execution_log` (future)
- Failed ETL does not overwrite existing reporting data
- Fix ETL script, re-run to replace reporting table

### 6.3 Monitoring & Alerting

**Current Monitoring:**
- Manual: Check BigQuery table row counts after ingestion
- Manual: Spot-check data quality with sample queries

**Future Monitoring (Phase 4):**
- Cloud Monitoring dashboards for ingestion success rate
- Alerting on ingestion failures (Slack/email)
- Data quality metrics (NULL rate, duplicate rate, foreign key violations)
- Query cost monitoring (optimize expensive queries)

---

## 7. Security & Access Control

### 7.1 BigQuery Access

**Current Access Model:**
- All datasets public within GCP project `chess-engine-metrics-agent`
- Service account authentication for automated ingestion
- User authentication via `gcloud auth application-default login`

**Future Access Model (Phase 4):**
- Role-based access control (RBAC)
- Read-only access for dashboard users
- Write access restricted to ingestion service accounts
- Audit logging for all data modifications

### 7.2 GCS Bucket Access

**Current Access Model:**
- Public write to `gs://v7p3r-raw-data/` (trusted users only)
- Service account read access for ingestion

**Security Considerations:**
- No sensitive data stored (all chess games public on Lichess)
- No PII (personally identifiable information)
- Engine source code NOT stored in analytics bucket

---

## 8. Cost Management

### 8.1 Storage Costs

**Current Monthly Estimate:**
- Raw Layer (GCS): ~10 GB × $0.02/GB = $0.20/month
- Conformed Layer (BigQuery): ~500 MB × $0.02/GB = $0.01/month
- Reporting Layer (BigQuery): ~50 MB × $0.02/GB = $0.001/month
- **Total Storage:** ~$0.21/month

### 8.2 Query Costs

**BigQuery Pricing:** $5 per TB scanned

**Cost Optimization Strategies:**
- **Clustering:** Tables clustered by common query dimensions (engine_version, date)
- **Partitioning:** Moves table partitioned by move_number (reduce scan size)
- **Projection:** SELECT only needed columns (avoid SELECT *)
- **Aggregation:** Use reporting layer instead of querying conformed layer
- **Caching:** BigQuery caches identical queries for 24 hours (free)

**Estimated Monthly Query Cost:**
- Development queries: ~10 GB scanned/month × $5/TB = $0.05/month
- Reporting ETLs: ~50 GB scanned/month × $5/TB = $0.25/month
- **Total Queries:** ~$0.30/month

**Total Estimated Cost:** ~$0.50/month (well within free tier)

---

## 9. Backup & Disaster Recovery

### 9.1 Backup Strategy

**Raw Layer (GCS):**
- **Backup:** GCS versioning enabled (retain 30 days of versions)
- **Recovery:** Restore previous version if file corrupted

**Conformed Layer (BigQuery):**
- **Backup:** BigQuery automatic 7-day time travel (query snapshots)
- **Recovery:** `SELECT * FROM conformed_layer.game_records FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)`
- **Long-term:** Export to GCS for archival (manual, quarterly)

**Reporting Layer (BigQuery):**
- **Backup:** None needed (can rebuild from conformed layer)
- **Recovery:** Re-run ETL scripts to regenerate reporting tables

### 9.2 Disaster Recovery Plan

**Scenario 1: Accidental Table Deletion**
- **Raw Layer:** Restore from GCS versioning
- **Conformed Layer:** Restore from 7-day time travel
- **Reporting Layer:** Re-run ETL scripts

**Scenario 2: Corrupted Data Ingestion**
- **Detection:** Row count spike, NULL rate increase
- **Recovery:** Delete corrupted rows by `ingested_at` timestamp, re-ingest from raw layer

**Scenario 3: GCP Project Deletion**
- **Prevention:** GCS bucket in separate project (future)
- **Recovery:** Restore from quarterly GCS export (if available)

---

## 10. Governance Roadmap

### Phase 1: Foundation (COMPLETE)
- ✅ Manual ingestion scripts for all data sources
- ✅ Source data contracts documented
- ✅ Conformed layer 8/15 tables complete
- ✅ Reporting layer 7 Tier 1 tables deployed

### Phase 2: Automation (Current - Phase 3)
- ⏳ Implement 7 Tier 1 ETL scripts
- ⏳ Schedule daily reporting layer refresh
- ⏳ Create data dictionaries

### Phase 3: Production Readiness (Phase 4)
- 🔲 Automate raw → conformed ingestion (Cloud Functions)
- 🔲 Implement contract validation in Cloud Functions
- 🔲 Set up monitoring dashboards
- 🔲 Configure alerting (Slack/email)

### Phase 4: Advanced Features (Future)
- 🔲 Stockfish integration for Tier 2 reporting
- 🔲 Real-time streaming ingestion
- 🔲 ML-based data quality anomaly detection
- 🔲 Self-service analytics dashboard

---

## Appendix A: Data Lineage

```
┌─────────────────────────────────────────────────────────────────────┐
│                          RAW LAYER (Bronze)                         │
│                     gs://v7p3r-raw-data/                           │
├─────────────────────────────────────────────────────────────────────┤
│  • PGN game files (game_records/*.pgn)                             │
│  • JSON analysis (analysis_results/*.json)                         │
│  • Documentation (v7p3r_docs/*.md)                                 │
│  • CSV datasets (reporting_datasets/*.csv)                         │
└────────────┬────────────────────────────────────────────────────────┘
             │
             │ Ingestion Scripts (scripts/ingestion/)
             │ Validated by Source Data Contracts (contracts/*.md)
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CONFORMED LAYER (Silver)                       │
│            chess-engine-metrics-agent.conformed_layer               │
├─────────────────────────────────────────────────────────────────────┤
│  • documentation (166 files)                                       │
│  • engine_versions (16 versions)                                   │
│  • operational_events (8 events)                                   │
│  • analysis_results (510 files)                                    │
│  • game_records (24,146 games)                                     │
│  • game_data (18,336 games)                                        │
│  • game_summary (18,336 summaries)                                 │
│  • moves (1,350,163 moves)                                         │
└────────────┬────────────────────────────────────────────────────────┘
             │
             │ ETL Scripts (scripts/reporting_etl/)
             │ Query conformed layer, aggregate metrics
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      REPORTING LAYER (Gold)                         │
│            chess-engine-metrics-agent.reporting_layer               │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 1 (Common KPIs):                                             │
│  • version_performance_summary                                     │
│  • opponent_strength_performance                                   │
│  • opening_performance                                             │
│  • time_control_performance                                        │
│  • temporal_trends                                                 │
│  • castling_analysis                                               │
│  • queen_trade_analysis                                            │
│                                                                     │
│  TIER 2 (Advanced Positional - Future):                           │
│  • move_quality_by_position (Stockfish required)                   │
│  • positional_weakness_patterns                                    │
│  • skill_level_correlations                                        │
│  • piece_activity_metrics                                          │
│  • material_imbalance_outcomes                                     │
│  • time_pressure_analysis                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Appendix B: Key Contacts

**Data Governance Owner:** V7P3R Analytics Team  
**Technical Lead:** User (pssnyder)  
**GCP Project:** chess-engine-metrics-agent  
**Documentation:** `docs/` directory in engine-metrics repo

---

**Document Version History:**
- v1.0 (2026-04-30): Initial data governance model created
