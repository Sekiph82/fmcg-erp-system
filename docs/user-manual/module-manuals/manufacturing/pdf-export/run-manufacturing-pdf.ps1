# Manufacturing Module Manual — PDF Generator (Windows PowerShell)
# Run from repo root:  .\docs\user-manual\module-manuals\manufacturing\pdf-export\run-manufacturing-pdf.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\..\..\..\"
$script = "$PSScriptRoot\generate-manufacturing-pdf.mjs"
$feDir = Join-Path $repoRoot "frontend"

Write-Host "`n=== Manufacturing Manual PDF — Windows Runner ===" -ForegroundColor Cyan
Write-Host "Repo root: $repoRoot"

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js not found. Install from https://nodejs.org/"
    exit 1
}
Write-Host "Node: $(node --version)"

# Check frontend node_modules
$playwrightPath = Join-Path $feDir "node_modules\playwright"
if (-not (Test-Path $playwrightPath)) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $feDir
    npm install
    Pop-Location
}

# Run generator
Write-Host "`nRunning PDF generator..." -ForegroundColor Green
node $script

$pdfPath = Join-Path $repoRoot "docs\user-manual\pdf-output\FMCG-ERP-Manufacturing-Manual.pdf"
if (Test-Path $pdfPath) {
    $size = [math]::Round((Get-Item $pdfPath).Length / 1MB, 1)
    Write-Host "`n✓ Output: $pdfPath ($size MB)" -ForegroundColor Green
} else {
    Write-Error "PDF not found at expected path: $pdfPath"
    exit 1
}
