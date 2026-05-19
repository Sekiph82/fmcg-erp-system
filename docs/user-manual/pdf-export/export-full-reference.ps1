# FMCG ERP Full Reference Manual — PDF Export Script (Windows PowerShell)
#
# Usage (from repo root):
#   .\docs\user-manual\pdf-export\export-full-reference.ps1
#
# Requirements:
#   - Node.js 18+
#   - frontend/node_modules/playwright installed
#   - frontend/node_modules/marked installed
#   - docs/user-manual/screenshots/captured/ exists with PNG files

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir))
if (-not (Test-Path "$RepoRoot\TASKS.md")) {
    $RepoRoot = (Get-Location).Path
}

Write-Host "=== FMCG ERP Full Reference Manual — PDF Export ===" -ForegroundColor Cyan
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
$fullRefDir = "$RepoRoot\docs\user-manual\full-reference"
$chapters = @(
    "00_FULL_ERP_MANUAL_INDEX.md",
    "01_DASHBOARD_AND_NAVIGATION.md",
    "02_MASTER_DATA.md",
    "03_PROCUREMENT.md",
    "04_INVENTORY_AND_WAREHOUSE.md",
    "05_PRODUCTION.md",
    "06_QUALITY_AND_COMPLIANCE.md",
    "07_SALES_AND_DISTRIBUTION.md",
    "08_FINANCE.md",
    "09_HR_AND_PAYROLL.md",
    "10_ADMIN_AND_SECURITY.md",
    "11_AI_AND_AUTOMATION.md",
    "12_REPORTS_AND_EXPORTS.md",
    "13_STANDALONE_OPERATIONAL_PAGES.md",
    "14_OLD_ROUTE_COMPATIBILITY.md"
)
$missing = $chapters | Where-Object { -not (Test-Path "$fullRefDir\$_") }
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
$script = "$RepoRoot\docs\user-manual\pdf-export\generate-full-reference-pdf.mjs"
node $script

if ($LASTEXITCODE -ne 0) {
    Write-Error "PDF generation failed (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}

# 6. Report
$pdf = "$outputDir\FMCG-ERP-Full-Reference-Manual.pdf"
if (Test-Path $pdf) {
    $sizeMb = [math]::Round((Get-Item $pdf).Length / 1MB, 1)
    Write-Host "`nPDF generated successfully!" -ForegroundColor Green
    Write-Host "Output: $pdf"
    Write-Host "Size:   $sizeMb MB"
} else {
    Write-Error "PDF not found at expected path: $pdf"
    exit 1
}
