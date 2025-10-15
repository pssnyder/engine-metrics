# V7P3R Data Sync Commands
# Quick reference for syncing V7P3R chess engine data with Firebase Storage

## Bucket Information
PROJECT_ID: chess-engine-metrics-agent
BUCKET: gs://chess-engine-metrics-agent.firebasestorage.app
LOCAL_DATA: ../raw_data

## Quick Sync Commands

### 1. Dry Run (see what would be synced)
gsutil -m rsync -r -n -c "../raw_data/analysis_results/v7p3r_analysis/" "gs://chess-engine-metrics-agent.firebasestorage.app/raw-data/analysis-results/v7p3r/"

### 2. Sync V7P3R Analysis Results (81 JSON files)
gsutil -m rsync -r -c -d "../raw_data/analysis_results/v7p3r_analysis/" "gs://chess-engine-metrics-agent.firebasestorage.app/raw-data/analysis-results/v7p3r/"

### 3. Sync Game Records (75 PGN files)
gsutil -m rsync -r -c -d "../raw_data/game_records/" "gs://chess-engine-metrics-agent.firebasestorage.app/raw-data/game-records/"

### 4. Sync All Raw Data
gsutil -m rsync -r -c -d "../raw_data/" "gs://chess-engine-metrics-agent.firebasestorage.app/raw-data/"

## Command Options Explained
-m    : Multithreaded (faster)
-r    : Recursive
-c    : Compare checksums (safer)
-d    : Delete extra files in destination
-n    : Dry run (show what would happen)

## Status Commands
# Check bucket contents
gsutil ls -r gs://chess-engine-metrics-agent.firebasestorage.app/

# Check specific directory
gsutil ls gs://chess-engine-metrics-agent.firebasestorage.app/raw-data/

# Get bucket info
gsutil du -sh gs://chess-engine-metrics-agent.firebasestorage.app/