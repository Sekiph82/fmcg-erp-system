# git-auto-sync.ps1
# Run by Claude Code Stop hook - stages, commits, and pushes all local changes.

$RepoPath = $PSScriptRoot
$LogFile  = "$RepoPath\git-sync.log"
$Branch   = "main"
$Remote   = "origin"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Invoke-Git {
    param([string[]]$GitArgs)
    $out = & git -C $RepoPath @GitArgs 2>&1
    return $out
}

Write-Log "-------------------------------------------"
Write-Log "Auto-sync started"

# Verify git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Log "git not found in PATH - aborting" "ERROR"
    exit 0
}

# Verify this is a git repo
$check = & git -C $RepoPath rev-parse --is-inside-work-tree 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "Not a git repository - aborting" "ERROR"
    exit 0
}

# Fetch to detect upstream changes
Write-Log "Fetching $Remote/$Branch..."
$fetchOut = Invoke-Git "fetch", $Remote, $Branch
Write-Log "Fetch: $fetchOut"

# Pull if behind remote
$behind = Invoke-Git "rev-list", "--count", "HEAD..${Remote}/${Branch}"
if ($behind -match "^\d+$" -and [int]$behind -gt 0) {
    Write-Log "Behind by $behind commit(s) - pulling..."
    $pullOut = Invoke-Git "pull", $Remote, $Branch, "--ff-only"
    Write-Log "Pull: $pullOut"
}

# Stage all changes (respects .gitignore - git-sync.log excluded)
Invoke-Git "add", "-A" | Out-Null

# Check if anything needs committing
$statusOut = Invoke-Git "status", "--porcelain"
if ([string]::IsNullOrWhiteSpace($statusOut)) {
    Write-Log "Working tree clean - nothing to commit"
    Write-Log "Auto-sync finished (no changes)"
    exit 0
}

# Count changed files
$lines        = $statusOut -split "`n" | Where-Object { $_ -ne "" }
$changedFiles = $lines.Count
$ts           = Get-Date -Format "yyyy-MM-dd HH:mm"
$commitMsg    = "Auto-sync: $changedFiles file(s) [$ts]"

Write-Log "Committing $changedFiles file(s)..."
$commitOut = Invoke-Git "commit", "-m", $commitMsg
Write-Log "Commit: $commitOut"

if ($LASTEXITCODE -ne 0) {
    Write-Log "Commit failed - aborting push" "ERROR"
    exit 0
}

# Push
Write-Log "Pushing to $Remote/$Branch..."
$pushOut = Invoke-Git "push", $Remote, $Branch
if ($LASTEXITCODE -ne 0) {
    Write-Log "Push failed: $pushOut" "ERROR"
    exit 0
}

Write-Log "Push successful"
Write-Log "Auto-sync finished - $changedFiles file(s) synced"
