# BigQuery Cleanup Script
# Deletes all old datasets and tables to prepare for new 3-layer architecture

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " BigQuery Cleanup - Strip to Frame" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$project = "chess-engine-metrics-agent"

Write-Host "This will DELETE all tables and datasets in:" -ForegroundColor Yellow
Write-Host "  - chess_engine_data_lake (3 tables)" -ForegroundColor Yellow
Write-Host "  - chess_analytics (1 table, 3 views)" -ForegroundColor Yellow
Write-Host "  - chess_reporting (5 tables)" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Are you sure you want to proceed? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "Cleanup cancelled." -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "[1/4] Deleting chess_engine_data_lake tables..." -ForegroundColor Cyan

Write-Host "  Deleting analysis_results..."
bq rm -f -t ${project}:chess_engine_data_lake.analysis_results

Write-Host "  Deleting documentation..."
bq rm -f -t ${project}:chess_engine_data_lake.documentation

Write-Host "  Deleting pgn_games..."
bq rm -f -t ${project}:chess_engine_data_lake.pgn_games

Write-Host "[2/4] Deleting chess_analytics views and tables..." -ForegroundColor Cyan

Write-Host "  Deleting development_timeline (view)..."
bq rm -f -t ${project}:chess_analytics.development_timeline

Write-Host "  Deleting engine_performance (view)..."
bq rm -f -t ${project}:chess_analytics.engine_performance

Write-Host "  Deleting head_to_head (view)..."
bq rm -f -t ${project}:chess_analytics.head_to_head

Write-Host "  Deleting ai_agent_insights (table)..."
bq rm -f -t ${project}:chess_analytics.ai_agent_insights

Write-Host "[3/4] Deleting chess_reporting tables..." -ForegroundColor Cyan

Write-Host "  Deleting daily_performance_trends..."
bq rm -f -t ${project}:chess_reporting.daily_performance_trends

Write-Host "  Deleting dashboard_kpis..."
bq rm -f -t ${project}:chess_reporting.dashboard_kpis

Write-Host "  Deleting engine_summary_stats..."
bq rm -f -t ${project}:chess_reporting.engine_summary_stats

Write-Host "  Deleting head_to_head_matrix..."
bq rm -f -t ${project}:chess_reporting.head_to_head_matrix

Write-Host "  Deleting v7p3r_development_timeline..."
bq rm -f -t ${project}:chess_reporting.v7p3r_development_timeline

Write-Host "[4/4] Deleting old datasets..." -ForegroundColor Cyan

Write-Host "  Deleting chess_engine_data_lake dataset..."
bq rm -r -f -d ${project}:chess_engine_data_lake

Write-Host "  Deleting chess_analytics dataset..."
bq rm -r -f -d ${project}:chess_analytics

Write-Host "  Deleting chess_reporting dataset..."
bq rm -r -f -d ${project}:chess_reporting

Write-Host ""
Write-Host "✅ Cleanup complete! BigQuery stripped to frame." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run .\scripts\setup_new_architecture.ps1 to create new datasets"
Write-Host "  2. Upload raw_data to GCS: .\scripts\upload_raw_data.ps1"
Write-Host "  3. Create external tables: .\scripts\create_external_tables.ps1"
Write-Host ""
