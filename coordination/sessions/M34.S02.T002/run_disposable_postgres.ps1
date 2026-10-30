param([string]$RunVersion = "V01")
$ErrorActionPreference = "Stop"
$repoRoot = "C:\Users\sekip\Desktop\fmcg-erp-system"
$backendRoot = Join-Path $repoRoot "backend"
$evidenceDirectory = Join-Path $repoRoot "coordination\sessions\M34.S02.T002"
New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
$transcriptPath = Join-Path $evidenceDirectory "disposable-postgres-run-$RunVersion.log"
$commandLogPath = Join-Path $evidenceDirectory "disposable-postgres-command-output-$RunVersion.log"
if ((Test-Path -LiteralPath $transcriptPath) -or (Test-Path -LiteralPath $commandLogPath)) {
    throw "Refusing to overwrite existing evidence for $RunVersion. Choose a new run version."
}
Start-Transcript -Path $transcriptPath -Force | Out-Null
$container = $null
$databaseName = $null
function Invoke-LoggedPython([string[]]$Arguments) {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & python @Arguments 2>&1 | Tee-Object -FilePath $commandLogPath -Append
        $nativeExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
    if ($nativeExitCode -ne 0) { throw "Python command failed ($nativeExitCode): python $($Arguments -join ' ')" }
}
try {
    $resolvedRoot = (git -C $repoRoot rev-parse --show-toplevel).Trim().Replace("/", "\")
    if ($resolvedRoot.TrimEnd("\") -ine $repoRoot) { throw "Refusing to run outside canonical checkout: $resolvedRoot" }
    Set-Location -LiteralPath $backendRoot
    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 24)
    $databaseName = "fmcg_m34_s02_t002_$suffix"
    $container = "codex-m34-s02-t002-$suffix"
    $existing = docker ps -a --filter "name=^/$container$" --format "{{.Names}}"
    if ($existing) { throw "Refusing to reuse existing container $container" }

    docker run -d --rm --name $container -e "POSTGRES_DB=$databaseName" -e POSTGRES_HOST_AUTH_METHOD=trust -p 127.0.0.1::5432 postgres:16-alpine
    if ($LASTEXITCODE -ne 0) { throw "Task-owned PostgreSQL container failed to start." }

    $endpoint = $null
    for ($i = 0; $i -lt 40; $i++) {
        $endpoint = docker port $container 5432/tcp 2>$null | Select-Object -First 1
        if ($endpoint) { break }
        Start-Sleep -Seconds 1
    }
    if (-not $endpoint) { throw "Docker did not publish the task database loopback port." }
    $port = ($endpoint -split ":")[-1].Trim()
    $env:DATABASE_URL = "postgresql+asyncpg://postgres@127.0.0.1:$port/$databaseName"
    $env:M34_S02_T002_DISPOSABLE_TEST_DATABASE = "1"
    $env:M34_S02_T002_DISPOSABLE_TEST_DATABASE_NAME = $databaseName
    Write-Output "DATABASE_NAME=$databaseName"
    Write-Output "CONTAINER_NAME=$container"
    Write-Output "POSTGRES_IMAGE=postgres:16-alpine"
    Write-Output "DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:$port/$databaseName (passwordless loopback)"

    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        docker exec $container pg_isready -U postgres -d $databaseName *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "Disposable PostgreSQL did not become ready." }

    Invoke-LoggedPython -Arguments @("-m", "alembic", "upgrade", "head")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "current")
    Invoke-LoggedPython -Arguments @("-m", "pytest", "-v", "tests/test_m34_s02_t002_bpa_price_breaks.py", "--tb=short")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "downgrade", "20261030_0008")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "current")
    $persistedBreakCount = docker exec $container psql -U postgres -d $databaseName -tA -c "SELECT COUNT(*) FROM blanket_agreement_price_breaks"
    if ($LASTEXITCODE -ne 0 -or [int]$persistedBreakCount.Trim() -ne 3) {
        throw "Price-break rows did not survive the migration downgrade: $persistedBreakCount"
    }
    Write-Output "BPA_PRICE_BREAK_ROWS_AFTER_DOWNGRADE=$($persistedBreakCount.Trim())"
    Invoke-LoggedPython -Arguments @("-m", "alembic", "upgrade", "head")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "current")
}
finally {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:M34_S02_T002_DISPOSABLE_TEST_DATABASE -ErrorAction SilentlyContinue
    Remove-Item Env:M34_S02_T002_DISPOSABLE_TEST_DATABASE_NAME -ErrorAction SilentlyContinue
    if ($container) {
        docker rm -f $container 2>$null | Out-Null
        $remaining = docker ps -a --filter "name=^/$container$" --format "{{.Names}}"
        if ($remaining) { Write-Error "Task-owned database container remains: $remaining" }
        else { Write-Output "TASK_CONTAINER_CLEANUP=verified_absent:$container" }
    }
    Stop-Transcript | Out-Null
}
