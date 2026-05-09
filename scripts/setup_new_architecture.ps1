# Setup New 3-Layer Lakehouse Architecture
# Creates raw_layer, conformed_layer, and reporting_layer datasets

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " BigQuery - Create New Architecture" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$project = "chess-engine-metrics-agent"
$location = "us-central1"

Write-Host "Creating 3-layer lakehouse architecture:" -ForegroundColor Yellow
Write-Host "  1. raw_layer - External tables → Cloud Storage" -ForegroundColor Yellow
Write-Host "  2. conformed_layer - Cleaned source of truth (15 tables)" -ForegroundColor Yellow
Write-Host "  3. reporting_layer - Aggregated analytics (6 views)" -ForegroundColor Yellow
Write-Host ""

Write-Host "[1/3] Creating raw_layer dataset..." -ForegroundColor Cyan
bq mk --dataset `
  --description="Raw layer - External tables pointing to Cloud Storage (Bronze)" `
  --location=$location `
  ${project}:raw_layer

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ raw_layer created" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  raw_layer might already exist or error occurred" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/3] Creating conformed_layer dataset..." -ForegroundColor Cyan
bq mk --dataset `
  --description="Conformed layer - Cleaned, deduplicated source of truth (Silver)" `
  --location=$location `
  ${project}:conformed_layer

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ conformed_layer created" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  conformed_layer might already exist or error occurred" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/3] Creating reporting_layer dataset..." -ForegroundColor Cyan
bq mk --dataset `
  --description="Reporting layer - Aggregated, optimized for consumption (Gold)" `
  --location=$location `
  ${project}:reporting_layer

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ reporting_layer created" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  reporting_layer might already exist or error occurred" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Current BigQuery datasets:" -ForegroundColor Cyan
Write-Host ""
bq ls --project_id=$project

Write-Host ""
Write-Host "✅ New architecture datasets created!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Upload raw_data to GCS: .\scripts\upload_raw_data.ps1"
Write-Host "  2. Create external tables: .\scripts\create_external_tables.ps1"
Write-Host "  3. Deploy Terraform for conformed_layer schemas"
Write-Host ""
