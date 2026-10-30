param([string]$RunVersion = "V05")
$ErrorActionPreference = "Stop"
$repoRoot = "C:\Users\sekip\Desktop\fmcg-erp-system"
$backendRoot = Join-Path $repoRoot "backend"
$evidenceDirectory = Join-Path $repoRoot "coordination\sessions\M34.S01.T003"
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
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($nativeExitCode -ne 0) { throw "Python command failed ($nativeExitCode): python $($Arguments -join ' ')" }
}
try {
    Set-Location -LiteralPath $backendRoot
    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 24)
    $databaseName = "fmcg_m34_s01_t003_$suffix"
    $container = "codex-m34-s01-t003-$suffix"
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
    $env:M34_S01_T003_DISPOSABLE_TEST_DATABASE = "1"
    $env:M34_S01_T003_DISPOSABLE_TEST_DATABASE_NAME = $databaseName
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
    Invoke-LoggedPython -Arguments @("-m", "alembic", "downgrade", "-1")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "upgrade", "head")

    $ownershipResetCommand = "DROP TABLE rfq_evaluation_migration_ownership;"
    docker exec $container psql -v ON_ERROR_STOP=1 -U postgres -d $databaseName -c $ownershipResetCommand 2>&1 | Tee-Object -FilePath $commandLogPath -Append
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare the synthetic pre-upgrade adoption state." }
    Invoke-LoggedPython -Arguments @("-m", "alembic", "stamp", "20261030_0006")

    $weakCheckCommand = "ALTER TABLE rfq_evaluation_criteria DROP CONSTRAINT ck_rfq_evaluation_criterion_weight_range; ALTER TABLE rfq_evaluation_criteria ADD CONSTRAINT ck_rfq_evaluation_criterion_weight_range CHECK (weight_percent > 0);"
    docker exec $container psql -v ON_ERROR_STOP=1 -U postgres -d $databaseName -c $weakCheckCommand 2>&1 | Tee-Object -FilePath $commandLogPath -Append
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare the synthetic weak-constraint adoption case." }
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & python -m alembic upgrade head 2>&1 | Tee-Object -FilePath $commandLogPath -Append
        $rejectedExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
    if ($rejectedExitCode -eq 0) { throw "Migration unexpectedly adopted an incompatible same-named weight constraint." }
    Write-Output "PARTIAL_SCHEMA_REJECTION=verified_incompatible_weight_check"

    $restoreCheckCommand = "ALTER TABLE rfq_evaluation_criteria DROP CONSTRAINT ck_rfq_evaluation_criterion_weight_range; ALTER TABLE rfq_evaluation_criteria ADD CONSTRAINT ck_rfq_evaluation_criterion_weight_range CHECK (weight_percent > 0 AND weight_percent <= 100 AND weight_percent NOT IN ('NaN', 'Infinity', '-Infinity'));"
    docker exec $container psql -v ON_ERROR_STOP=1 -U postgres -d $databaseName -c $restoreCheckCommand 2>&1 | Tee-Object -FilePath $commandLogPath -Append
    if ($LASTEXITCODE -ne 0) { throw "Could not restore the exact synthetic evaluation constraint." }

    $weakPrimaryKeyCommand = "ALTER TABLE rfq_response_evaluations DROP CONSTRAINT rfq_response_evaluations_criterion_id_fkey; ALTER TABLE rfq_evaluation_criteria DROP CONSTRAINT rfq_evaluation_criteria_pkey; ALTER TABLE rfq_evaluation_criteria ADD CONSTRAINT rfq_evaluation_criteria_pkey PRIMARY KEY (rfq_id);"
    docker exec $container psql -v ON_ERROR_STOP=1 -U postgres -d $databaseName -c $weakPrimaryKeyCommand 2>&1 | Tee-Object -FilePath $commandLogPath -Append
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare the synthetic incompatible-primary-key adoption case." }
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & python -m alembic upgrade head 2>&1 | Tee-Object -FilePath $commandLogPath -Append
        $rejectedExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
    if ($rejectedExitCode -eq 0) { throw "Migration unexpectedly adopted an evaluation table with an incompatible primary key." }
    Write-Output "PARTIAL_SCHEMA_REJECTION=verified_incompatible_primary_key"

    $restorePrimaryKeyCommand = "ALTER TABLE rfq_evaluation_criteria DROP CONSTRAINT rfq_evaluation_criteria_pkey; ALTER TABLE rfq_evaluation_criteria ADD CONSTRAINT rfq_evaluation_criteria_pkey PRIMARY KEY (id); ALTER TABLE rfq_response_evaluations ADD CONSTRAINT rfq_response_evaluations_criterion_id_fkey FOREIGN KEY (criterion_id) REFERENCES rfq_evaluation_criteria(id) ON DELETE CASCADE;"
    docker exec $container psql -v ON_ERROR_STOP=1 -U postgres -d $databaseName -c $restorePrimaryKeyCommand 2>&1 | Tee-Object -FilePath $commandLogPath -Append
    if ($LASTEXITCODE -ne 0) { throw "Could not restore the exact synthetic evaluation primary key." }
    Invoke-LoggedPython -Arguments @("-m", "alembic", "upgrade", "head")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "downgrade", "-1")

    $legacySchemaCommand = "DROP TABLE IF EXISTS rfq_response_evaluations; DROP TABLE IF EXISTS rfq_evaluation_criteria; ALTER TABLE rfq_responses DROP COLUMN IF EXISTS evaluation_status; DROP TYPE IF EXISTS rfqevaluationstatus; DROP TYPE IF EXISTS rfqevaluationdimension;"
    docker exec $container psql -v ON_ERROR_STOP=1 -U postgres -d $databaseName -c $legacySchemaCommand 2>&1 | Tee-Object -FilePath $commandLogPath -Append
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare the synthetic pre-evaluation schema in the task-owned database." }

    Invoke-LoggedPython -Arguments @("-m", "alembic", "upgrade", "head")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "current")
    Invoke-LoggedPython -Arguments @("-m", "pytest", "-q", "tests/test_m34_s01_t003_rfq_evaluation_matrix.py", "--tb=short")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "downgrade", "-1")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "upgrade", "head")
    Invoke-LoggedPython -Arguments @("-m", "alembic", "current")
}
finally {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:M34_S01_T003_DISPOSABLE_TEST_DATABASE -ErrorAction SilentlyContinue
    Remove-Item Env:M34_S01_T003_DISPOSABLE_TEST_DATABASE_NAME -ErrorAction SilentlyContinue
    if ($container) {
        docker rm -f $container 2>$null | Out-Null
        $remaining = docker ps -a --filter "name=^/$container$" --format "{{.Names}}"
        if ($remaining) { Write-Error "Task-owned database container remains: $remaining" }
        else { Write-Output "TASK_CONTAINER_CLEANUP=verified_absent:$container" }
    }
    Stop-Transcript | Out-Null
}
