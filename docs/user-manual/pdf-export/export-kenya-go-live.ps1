# Kenya Go-Live ERP Training Manual — PDF Export Script (Windows PowerShell)
#
# Usage:
#   cd C:\path\to\fmcg-erp-system-main
#   .\docs\user-manual\pdf-export\export-kenya-go-live.ps1
#
# Requirements:
#   - Node.js 18+
#   - frontend/node_modules/playwright installed
#   - frontend/node_modules/marked installed
#   - docs/user-manual/screenshots/captured/ exists with PNG files

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
# If invoked from repo root via relative path, use current dir
if (-not (Test-Path "$RepoRoot\TASKS.md")) {
    $RepoRoot = (Get-Location).Path
}

Write-Host "=== Kenya Go-Live PDF Export ===" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot"

# 1. Verify screenshots
$screenshotsDir = "$RepoRoot\docs\user-manual\screenshots\captured"
if (-not (Test-Path $screenshotsDir)) {
    Write-Error "Screenshots folder missing: $screenshotsDir"
    Write-Host "Regenerate: cd frontend; `$env:E2E_SKIP_WEBSERVER=1; npx playwright test e2e/manual-screenshots.spec.ts --project=chromium"
    exit 1
}
$pngCount = (Get-ChildItem $screenshotsDir -Filter "*.png").Count
Write-Host "Screenshots: $pngCount PNGs found"
if ($pngCount -lt 100) {
    Write-Warning "Only $pngCount screenshots found. Expected ~140. PDF may have missing images."
}

# 2. Verify node_modules
$frontendModules = "$RepoRoot\frontend\node_modules"
if (-not (Test-Path "$frontendModules\playwright")) {
    Write-Error "Playwright not found at $frontendModules\playwright"
    Write-Host "Fix: cd frontend; npm install"
    exit 1
}
if (-not (Test-Path "$frontendModules\marked")) {
    Write-Error "marked not found at $frontendModules\marked"
    Write-Host "Fix: cd frontend; npm install --save-dev marked"
    exit 1
}

# 3. Verify chapters
$kenyaDir = "$RepoRoot\docs\user-manual\kenya-go-live"
$chapters = @(
    "00_GO_LIVE_TRAINING_INDEX.md",
    "01_ADMIN_USER_MANUAL.md",
    "02_PRODUCTION_USER_MANUAL.md",
    "03_WAREHOUSE_INVENTORY_USER_MANUAL.md",
    "04_PROCUREMENT_USER_MANUAL.md",
    "05_QUALITY_CONTROL_USER_MANUAL.md",
    "06_SALES_LOGISTICS_USER_MANUAL.md",
    "07_HR_USER_MANUAL.md",
    "08_MANAGER_DASHBOARD_USER_MANUAL.md",
    "09_COMMON_PROBLEMS_AND_FAQ.md"
)
$missing = $chapters | Where-Object { -not (Test-Path "$kenyaDir\$_") }
if ($missing) {
    Write-Error "Missing chapter files: $($missing -join ', ')"
    exit 1
}
Write-Host "Chapters: $($chapters.Count) files verified"

# 4. Create output directory
$outputDir = "$RepoRoot\docs\user-manual\pdf-output"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

# 5. Generate PDF
Write-Host "`nRunning PDF generator..." -ForegroundColor Cyan
$script = "$RepoRoot\docs\user-manual\pdf-export\generate-kenya-pdf.mjs"
node $script

if ($LASTEXITCODE -ne 0) {
    Write-Error "PDF generation failed (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}

# 6. Report
$pdf = "$outputDir\Kenya-Go-Live-ERP-Training-Manual.pdf"
if (Test-Path $pdf) {
    $sizeMb = [math]::Round((Get-Item $pdf).Length / 1MB, 1)
    Write-Host "`nPDF generated successfully!" -ForegroundColor Green
    Write-Host "Output: $pdf"
    Write-Host "Size:   $sizeMb MB"
} else {
    Write-Error "PDF not found at expected path: $pdf"
    exit 1
}
