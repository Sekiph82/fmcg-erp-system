# ─────────────────────────────────────────────────────────────────────────────
# git-auto-sync.ps1
# Automatically stages, commits, and pushes all local changes to GitHub.
# Designed to be run by Windows Task Scheduler on a schedule.
# ─────────────────────────────────────────────────────────────────────────────

$RepoPath = "C:\Users\sekip\Desktop\fmcg-erp-system-main"
$LogFile  = "$RepoPath\git-sync.log"
$Branch   = "main"
$Remote   = "origin"

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] [$Level] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Invoke-Git {
    param([string[]]$Args)
    $result = & git @Args 2>&1
    return $result
}

# ── Main ──────────────────────────────────────────────────────────────────────

Write-Log "───────────────────────────────────────────"
Write-Log "Auto-sync started"

# Go to repo
Set-Location $RepoPath

# Check git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Log "git not found in PATH — aborting" "ERROR"
    exit 1
}

# Fetch remote to detect any upstream changes
Write-Log "Fetching from $Remote/$Branch..."
$fetchOut = Invoke-Git "fetch", $Remote, $Branch
Write-Log "Fetch: $fetchOut"

# Check for upstream changes we don't have
$behind = Invoke-Git "rev-list", "--count", "HEAD..${Remote}/${Branch}"
if ($behind -gt 0) {
    Write-Log "Local branch is $behind commit(s) behind remote — pulling first..."
    $pullOut = Invoke-Git "pull", $Remote, $Branch, "--ff-only"
    Write-Log "Pull: $pullOut"
}

# Stage everything (respects .gitignore — .claude/ and git-sync.log are excluded)
$stageOut = Invoke-Git "add", "-A"

# Check if there is anything to commit
$statusOut = Invoke-Git "status", "--porcelain"
if ([string]::IsNullOrWhiteSpace($statusOut)) {
    Write-Log "No changes to commit — working tree clean"
    Write-Log "Auto-sync finished (nothing to do)"
    exit 0
}

# Count changed files for commit message
$changedFiles = ($statusOut -split "`n" | Where-Object { $_ -ne "" }).Count
$timestamp    = Get-Date -Format "yyyy-MM-dd HH:mm"

# Build commit message
$commitMsg = "Auto-sync: $changedFiles file(s) updated [$timestamp]"

Write-Log "Committing $changedFiles file(s)..."
$commitOut = Invoke-Git "commit", "-m", $commitMsg
Write-Log "Commit: $commitOut"

# Push
Write-Log "Pushing to $Remote/$Branch..."
$pushOut = Invoke-Git "push", $Remote, $Branch
if ($LASTEXITCODE -ne 0) {
    Write-Log "Push failed: $pushOut" "ERROR"
    exit 1
}

Write-Log "Push successful: $pushOut"
Write-Log "Auto-sync finished — $changedFiles file(s) synced"
