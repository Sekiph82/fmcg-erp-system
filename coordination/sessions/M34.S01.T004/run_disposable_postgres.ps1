param([string]$RunVersion = "V01")
$ErrorActionPreference = "Stop"
$repoRoot = "C:\Users\sekip\Desktop\fmcg-erp-system"
$backendRoot = Join-Path $repoRoot "backend"
$evidenceDirectory = Join-Path $repoRoot "coordination\sessions\M34.S01.T004"
New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
$transcriptPath = Join-Path $evidenceDirectory "disposable-postgres-run-$RunVersion.log"
$commandLogPath = Join-Path $evidenceDirectory "disposable-postgres-command-output-$RunVersion.log"
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
function Invoke-LoggedPsql([string]$Sql) {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        docker exec $container psql -v ON_ERROR_STOP=1 -U postgres -d $databaseName -c $Sql 2>&1 |
            Tee-Object -FilePath $commandLogPath -Append
        $nativeExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
    if ($nativeExitCode -ne 0) { throw "Disposable database SQL failed ($nativeExitCode)." }
}
try {
    $resolvedRoot = (git -C $repoRoot rev-parse --show-toplevel).Trim().Replace("/", "\")
    if ($resolvedRoot.TrimEnd("\") -ine $repoRoot) { throw "Refusing to run outside canonical checkout: $resolvedRoot" }
    Set-Location -LiteralPath $backendRoot
    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 24)
    $databaseName = "fmcg_m34_s01_t004_$suffix"
    $container = "codex-m34-s01-t004-$suffix"
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
    $env:M34_S01_T004_DISPOSABLE_TEST_DATABASE = "1"
    $env:M34_S01_T004_DISPOSABLE_TEST_DATABASE_NAME = $databaseName
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

    # Verify downgrade/re-upgrade on empty task-owned award objects before
    # retaining synthetic approval history in the database.
    Invoke-LoggedPython -Arguments @("-m", "alembic", "downgrade", "-1")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "upgrade", "head")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "current")

    # Existing exact-shape tables are created by the squashed baseline from
    # current metadata. Verify that an incompatible version fails closed.
    Invoke-LoggedPython -Arguments @("-m", "alembic", "downgrade", "-1")
    Invoke-LoggedPsql "ALTER TABLE rfq_award_allocations DROP CONSTRAINT ck_rfq_award_allocation_quantity_positive; ALTER TABLE rfq_award_allocations ADD CONSTRAINT ck_rfq_award_allocation_quantity_positive CHECK (quantity > 0);"
    Invoke-LoggedPython -Arguments @("-m", "alembic", "stamp", "20261030_0007")
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & python -m alembic upgrade head 2>&1 | Tee-Object -FilePath $commandLogPath -Append
        $rejectedExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
    if ($rejectedExitCode -eq 0) { throw "Migration unexpectedly adopted an incompatible award allocation table." }
    Write-Output "INCOMPATIBLE_SCHEMA_REJECTION=verified_weak_quantity_check"
    Invoke-LoggedPsql "ALTER TABLE rfq_award_allocations DROP CONSTRAINT ck_rfq_award_allocation_quantity_positive; ALTER TABLE rfq_award_allocations ADD CONSTRAINT ck_rfq_award_allocation_quantity_positive CHECK (quantity > 0 AND quantity NOT IN ('NaN', 'Infinity', '-Infinity'));"
    Invoke-LoggedPython -Arguments @("-m", "alembic", "upgrade", "head")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "current")

    Invoke-LoggedPython -Arguments @("-m", "pytest", "-q", "tests/test_m34_s01_t004_rfq_award_approval.py", "tests/test_m34_s01_t002_rfq_bids.py", "tests/test_m34_s01_t003_rfq_evaluation_matrix.py", "--tb=short")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "current")
}
finally {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:M34_S01_T004_DISPOSABLE_TEST_DATABASE -ErrorAction SilentlyContinue
    Remove-Item Env:M34_S01_T004_DISPOSABLE_TEST_DATABASE_NAME -ErrorAction SilentlyContinue
    if ($container) {
        docker rm -f $container 2>$null | Out-Null
        $remaining = docker ps -a --filter "name=^/$container$" --format "{{.Names}}"
        if ($remaining) { Write-Error "Task-owned database container remains: $remaining" }
        else { Write-Output "TASK_CONTAINER_CLEANUP=verified_absent:$container" }
    }
    Stop-Transcript | Out-Null
}
