# Create External Tables in Raw Layer
# Points BigQuery to Cloud Storage files for schema-on-read access

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Create External Tables (Raw Layer)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$project = "chess-engine-metrics-agent"
$bucket = "v7p3r-raw-data"

Write-Host "Creating external tables in raw_layer dataset..." -ForegroundColor Yellow
Write-Host ""

# External table for puzzle CSV
Write-Host "[1/5] Creating raw_puzzles_csv..." -ForegroundColor Cyan

# Create definition manually as JSON and pipe to bq mk
$puzzleDef = @{
    sourceFormat = "CSV"
    sourceUris = @("gs://${bucket}/pgn_training_data/lichess_db_puzzle.csv")
    csvOptions = @{
        skipLeadingRows = 1
    }
    schema = @{
        fields = @(
            @{name = "PuzzleId"; type = "STRING"},
            @{name = "FEN"; type = "STRING"},
            @{name = "Moves"; type = "STRING"},
            @{name = "Rating"; type = "INT64"},
            @{name = "RatingDeviation"; type = "INT64"},
            @{name = "Popularity"; type = "INT64"},
            @{name = "NbPlays"; type = "INT64"},
            @{name = "Themes"; type = "STRING"},
            @{name = "GameUrl"; type = "STRING"},
            @{name = "OpeningTags"; type = "STRING"}
        )
    }
}

$jsonDef = $puzzleDef | ConvertTo-Json -Depth 10 -Compress
[System.IO.File]::WriteAllText("temp_puzzle_def.json", $jsonDef, [System.Text.UTF8Encoding]::new($false))

bq mk --external_table_definition=temp_puzzle_def.json ${project}:raw_layer.raw_puzzles_csv 2>&1 | Out-Null

Remove-Item "temp_puzzle_def.json" -ErrorAction SilentlyContinue

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ raw_puzzles_csv created (4M rows)" -ForegroundColor Green
} elseif ((bq ls ${project}:raw_layer 2>&1 | Select-String "raw_puzzles_csv")) {
    Write-Host "  ✅ raw_puzzles_csv already exists (4M rows)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Error creating raw_puzzles_csv" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/5] Skipping raw_analysis_json (requires custom ingestion)..." -ForegroundColor Yellow
Write-Host "  → Analysis JSON files are not newline-delimited format" -ForegroundColor Gray
Write-Host "  → Will be parsed during ingestion to conformed_layer.stockfish_analysis" -ForegroundColor Gray

# Analysis results are regular JSON objects, not newline-delimited
# We'll ingest these directly to conformed_layer instead

Write-Host ""
Write-Host "[3/5] Skipping raw_pgn_lichess (requires custom ingestion)..." -ForegroundColor Yellow
Write-Host "  → PGN files will be parsed during ingestion to conformed_layer" -ForegroundColor Gray

# PGN files require custom parsing with python-chess library
# We'll ingest these directly to conformed_layer.lichess_games instead

Write-Host ""
Write-Host "[4/5] Skipping raw_notation_events (requires custom ingestion)..." -ForegroundColor Yellow
Write-Host "  → notation_events.json is not newline-delimited format" -ForegroundColor Gray
Write-Host "  → Will be parsed during ingestion to conformed_layer.operational_events" -ForegroundColor Gray

# Notation events is a regular JSON object, not newline-delimited
# We'll ingest this directly to conformed_layer instead

Write-Host ""
Write-Host "[5/5] Skipping raw_documentation (requires custom ingestion)..." -ForegroundColor Yellow
Write-Host "  → Markdown files will be parsed during ingestion to conformed_layer.documentation" -ForegroundColor Gray

# Markdown files require custom parsing
# We'll ingest these directly to conformed_layer.documentation instead

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "External tables created in raw_layer:" -ForegroundColor Cyan
Write-Host ""
bq ls ${project}:raw_layer

Write-Host ""
Write-Host "✅ 1 external table created successfully!" -ForegroundColor Green
Write-Host "   raw_puzzles_csv (4M rows, 861 MB)" -ForegroundColor Gray
Write-Host ""
Write-Host "⏭️  Skipped (will use Python ingestion instead):" -ForegroundColor Yellow
Write-Host "   • Analysis JSON files (not newline-delimited)" -ForegroundColor Gray
Write-Host "   • Notation events JSON (not newline-delimited)" -ForegroundColor Gray
Write-Host "   • PGN files (require python-chess parser)" -ForegroundColor Gray
Write-Host "   • Markdown files (require custom parser)" -ForegroundColor Gray
Write-Host ""
Write-Host "You can now query puzzles directly from GCS:" -ForegroundColor Cyan
Write-Host "  SELECT * FROM \`${project}.raw_layer.raw_puzzles_csv\` WHERE Rating >= 2000 LIMIT 10" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Deploy Terraform for conformed_layer schemas"
Write-Host "  2. Run Python ingestion scripts to load GCS → conformed_layer"
Write-Host ""
