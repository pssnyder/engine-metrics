# Upload Raw Data to Cloud Storage
# Syncs local raw_data directory to GCS bucket

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Upload Raw Data to Cloud Storage" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$bucket = "v7p3r-raw-data"
$project = "chess-engine-metrics-agent"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$localPath = "raw_data"

# Change to project root so we can use relative path (avoids PowerShell quoting issues with spaces)
Push-Location $projectRoot

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Project: $project" -ForegroundColor Yellow
Write-Host "  Bucket: gs://$bucket/" -ForegroundColor Yellow
Write-Host "  Local Path: $localPath (relative)" -ForegroundColor Yellow
Write-Host ""

# Check if bucket exists
Write-Host "Checking if bucket exists..." -ForegroundColor Cyan
$bucketExists = gsutil ls -p $project | Select-String $bucket

if (-not $bucketExists) {
    Write-Host "Bucket does not exist. Creating gs://$bucket/..." -ForegroundColor Yellow
    gsutil mb -p $project -l us-central1 -c STANDARD gs://$bucket/
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Bucket created" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to create bucket" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  ✅ Bucket already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting upload (this may take several minutes for 2.58 GB)..." -ForegroundColor Cyan
Write-Host ""

# Upload with rsync (only uploads new/changed files)
# Using relative path to avoid PowerShell quoting issues with spaces in absolute paths
gsutil -m rsync -r $localPath gs://$bucket/

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Upload complete!" -ForegroundColor Green
    
    # Show bucket contents summary
    Write-Host ""
    Write-Host "Bucket contents:" -ForegroundColor Cyan
    gsutil du -sh gs://$bucket/*
    
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Create external tables: .\scripts\create_external_tables.ps1"
    Write-Host "  2. Deploy Terraform for conformed_layer schemas"
    
    # Return to original directory
    Pop-Location
} else {
    Write-Host ""
    Write-Host "❌ Upload failed" -ForegroundColor Red
    
    # Return to original directory
    Pop-Location
    exit 1
}
