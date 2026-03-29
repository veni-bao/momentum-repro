# Momentum Reproduction - Test Scripts
# Run this from project root

param(
    [switch]$All,
    [switch]$Mock,
    [switch]$Full
)

$ErrorActionPreference = "Stop"

# Get project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = $ScriptDir
Set-Location $ProjectRoot

Write-Host "=" * 50
Write-Host "Momentum Reproduction Tests"
Write-Host "=" * 50

# Step 1: Setup or check environment
if (-not (Test-Path ".venv")) {
    Write-Host "[1/4] Setting up uv environment..."
    uv sync
} else {
    Write-Host "[1/4] uv environment already exists"
}

# Step 2: Run mock data test
if ($All -or $Mock) {
    Write-Host "[2/4] Running mock data test..."
    python -m data.mock.test_run
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Mock test failed" -ForegroundColor Red
        exit 1
    }
}

# Step 3: Run full pipeline test (if exists)
if ($Full -or $All) {
    Write-Host "[3/4] Running full pipeline test..."
    if (Test-Path "src/factors/test_pipeline.py") {
        python -m src.factors.test_pipeline
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Pipeline test failed" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Skipping: test_pipeline.py not found" -ForegroundColor Yellow
    }
}

Write-Host "[4/4] Done!" -ForegroundColor Green

Write-Host ""
Write-Host "=" * 50
Write-Host "Test completed successfully!"
Write-Host "=" * 50