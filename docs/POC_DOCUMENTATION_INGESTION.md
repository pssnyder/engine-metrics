# Documentation Ingestion - Proof of Concept

This is our first end-to-end ingestion pipeline: GCS → Python → BigQuery

## What We're Building

**Table:** `conformed_layer.documentation`  
**Source:** 173 markdown files in `gs://v7p3r-raw-data/v7p3r_docs/`  
**Target:** Searchable documentation table in BigQuery

## Execution Steps

### Step 1: Deploy Terraform Schema

```powershell
cd terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply (create the documentation table)
terraform apply
```

**Expected output:**
```
Plan: 4 to add, 0 to change, 0 to destroy
  + google_bigquery_dataset.raw_layer
  + google_bigquery_dataset.conformed_layer  
  + google_bigquery_dataset.reporting_layer
  + google_bigquery_table.documentation
```

**Note:** If datasets already exist from PowerShell scripts, Terraform will try to create them again. We'll handle this in a moment.

---

### Step 2: Test Ingestion (Dry Run)

```powershell
cd ../scripts/ingestion

# Dry run - processes files but doesn't insert
python 01_ingest_documentation.py --dry-run
```

**Expected output:**
```
INFO - Fetching files from gs://v7p3r-raw-data/v7p3r_docs/
INFO - Found 173 markdown files
INFO - Processing 1/173: v7p3r_docs/CHANGELOG.md
...
INFO - Processed 173 files successfully
INFO - DRY RUN - Skipping BigQuery insert
```

---

### Step 3: Run Full Ingestion

```powershell
# Production run - inserts to BigQuery
python 01_ingest_documentation.py
```

**Expected output:**
```
INFO - Inserting 173 rows to BigQuery...
INFO - ✅ Successfully ingested 173 documentation files
INFO - Verifying ingestion:
INFO -   general: 45 files, 1,234,567 bytes, 123,456 words
INFO -   development: 38 files, 987,654 bytes, 98,765 words
INFO -   configuration: 22 files, 456,789 bytes, 45,678 words
...
```

---

### Step 4: Query the Data

```sql
-- Search documentation
SELECT file_path, category, word_count
FROM `chess-engine-metrics-agent.conformed_layer.documentation`
WHERE LOWER(content) LIKE '%version%'
ORDER BY word_count DESC
LIMIT 10;

-- Category summary
SELECT 
    category,
    COUNT(*) as file_count,
    SUM(file_size_bytes) / 1024 / 1024 as total_mb,
    AVG(word_count) as avg_words
FROM `chess-engine-metrics-agent.conformed_layer.documentation`
GROUP BY category
ORDER BY file_count DESC;
```

---

## Troubleshooting

### Issue: "Table not found" error

**Cause:** Terraform hasn't been applied yet  
**Solution:** Run `terraform apply` first

### Issue: "Dataset already exists" error from Terraform

**Cause:** Datasets created by PowerShell scripts  
**Solution:** Import existing resources:
```powershell
terraform import google_bigquery_dataset.raw_layer chess-engine-metrics-agent/raw_layer
terraform import google_bigquery_dataset.conformed_layer chess-engine-metrics-agent/conformed_layer
terraform import google_bigquery_dataset.reporting_layer chess-engine-metrics-agent/reporting_layer
```

### Issue: "Permission denied" error

**Cause:** Application default credentials not set  
**Solution:**
```powershell
gcloud auth application-default login
```

---

## Success Criteria

- ✅ Terraform applies successfully (1 table created)
- ✅ Python script runs without errors
- ✅ 173 rows inserted to BigQuery
- ✅ Can query documentation content
- ✅ Pattern validated for scaling to other tables

---

## Next Steps After Success

Once this works, we'll scale the pattern to:
1. `engine_versions` - Version history
2. `operational_events` - Event logs
3. `stockfish_analysis` - Analysis results JSON
4. `puzzles` - 4M puzzles from external table
5. `lichess_games` - PGN parsing with python-chess
6. ... 10 more tables

**One table at a time, with your feedback at each step!** 🚀
