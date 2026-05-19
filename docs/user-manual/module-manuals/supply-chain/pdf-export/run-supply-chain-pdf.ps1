# FMCG ERP Supply Chain Module Manual — PDF Generator (PowerShell)
# Run from repo root:
#   .\docs\user-manual\module-manuals\supply-chain\pdf-export\run-supply-chain-pdf.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.Parent.Parent.FullName
$Generator = Join-Path $PSScriptRoot "generate-supply-chain-pdf.mjs"
$FrontendDir = Join-Path $RepoRoot "frontend"

Write-Host ""
Write-Host "=== Supply Chain PDF Generator ===" -ForegroundColor Green
Write-Host "Repo root: $RepoRoot"
Write-Host "Generator: $Generator"
Write-Host ""

# Ensure frontend dependencies are installed
if (-not (Test-Path (Join-Path $FrontendDir "node_modules" "playwright"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

# Run generator
Write-Host "Running PDF generator..." -ForegroundColor Cyan
node $Generator

Write-Host ""
Write-Host "Output: docs\user-manual\pdf-output\FMCG-ERP-Supply-Chain-Manual.pdf" -ForegroundColor Green
