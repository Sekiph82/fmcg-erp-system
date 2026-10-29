# Run M31.S02.T002 event-schema tests on a loopback-only disposable PostgreSQL database.
$ErrorActionPreference = 'Continue'

function Invoke-Docker {
    param([string[]]$Arguments)
    $output = @(& docker @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { throw "Docker command failed ($($Arguments -join ' ')): $($output -join ' ')" }
    return ($output -join "`n").Trim()
}

$image = 'postgres:16-alpine'
$user = 'fmcg_m31_s02_t002_test'
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 20)
$database = "fmcg_m31_s02_t002_$suffix"
$container = "codex-m31-s02-t002-$suffix"
$legacyDefinitionId = [Guid]::NewGuid().ToString()
$legacyEventCode = "test.m31.s02.t002.migrated.$suffix"
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL
$previousTaskGate = $env:M31_S02_T002_DISPOSABLE_TEST_DATABASE
$previousTaskDatabase = $env:M31_S02_T002_DISPOSABLE_TEST_DATABASE_NAME
$previousLegacyId = $env:M31_S02_T002_LEGACY_DEFINITION_ID
$previousLegacyCode = $env:M31_S02_T002_LEGACY_EVENT_CODE
$sessionPath = Join-Path $PSScriptRoot "postgres-test-run-$suffix.log"
$pytestPath = Join-Path $PSScriptRoot "pytest-output-$suffix.log"
Start-Transcript -Path $sessionPath -Force | Out-Null
try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Local PostgreSQL image ID was not returned.' }
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M31.S02.T002',
        '--label', 'codex.disposable=true', '--label', 'codex.database-purpose=M31-event-schema-tests',
        '--publish', '127.0.0.1::5432',
        '--env', "POSTGRES_USER=$user", '--env', "POSTGRES_DB=$database",
        '--env', 'POSTGRES_HOST_AUTH_METHOD=trust', $image
    )
    $started = $true
    $ready = $false
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        & docker exec $container pg_isready -U $user -d $database *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Disposable PostgreSQL did not become ready within 90 seconds.' }
    $binding = Invoke-Docker @('port', $container, '5432/tcp')
    if ($binding -match '^127\.0\.0\.1:(\d+)$') { $port = $Matches[1] }
    else { throw "Database port was not loopback-only: $binding" }

    $backend = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\backend'))
    Push-Location $backend
    try {
        $env:DATABASE_URL = "postgresql+asyncpg://$user@127.0.0.1:$port/$database"
        $env:M31_S02_T002_DISPOSABLE_TEST_DATABASE = '1'
        $env:M31_S02_T002_DISPOSABLE_TEST_DATABASE_NAME = $database
        $migrationOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        if ($LASTEXITCODE -ne 0) { throw "Fresh migration to head failed: $($migrationOutput -join ' ')" }
        $downgradeOutput = @(& .\venv\Scripts\python.exe -m alembic downgrade 20261029_0043 2>&1)
        if ($LASTEXITCODE -ne 0) { throw "Disposable database could not be returned to the pre-task schema: $($downgradeOutput -join ' ')" }
        $legacySchema = '{"type":"object","properties":{"status":{"type":"string"}},"required":["status"],"additionalProperties":false}'
        $legacyInsert = "INSERT INTO webhook_event_definitions (id, event_code, event_name, module, payload_schema, active_flag) VALUES ('$legacyDefinitionId', '$legacyEventCode', 'Synthetic migrated definition', 'testing', '$legacySchema'::jsonb, true);"
        $null = Invoke-Docker @(
            'exec', $container, 'psql', '-U', $user, '-d', $database,
            '-v', 'ON_ERROR_STOP=1', '-c', $legacyInsert
        )
        $upgradeOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        if ($LASTEXITCODE -ne 0) { throw "Upgrade from the pre-versioning event schema failed: $($upgradeOutput -join ' ')" }
        $env:M31_S02_T002_LEGACY_DEFINITION_ID = $legacyDefinitionId
        $env:M31_S02_T002_LEGACY_EVENT_CODE = $legacyEventCode
        $testOutput = @(& .\venv\Scripts\python.exe -m pytest -q --tb=short tests\test_m31_s02_t002_event_schema_governance_db.py 2>&1)
        $testOutput | Out-File -LiteralPath $pytestPath -Encoding utf8
        $testOutput
        if ($LASTEXITCODE -ne 0) { throw 'M31.S02.T002 PostgreSQL event-schema checks failed.' }
        $current = (& .\venv\Scripts\python.exe -m alembic current 2>&1) -join "`n"
        if ($LASTEXITCODE -ne 0 -or $current -notmatch '20261030_0001') { throw "Could not confirm final migration revision: $current" }
    }
    finally { Pop-Location }

    Write-Output 'RESULT=PASS'
    Write-Output "POSTGRES_IMAGE=$image"
    Write-Output "POSTGRES_IMAGE_ID=$imageId"
    Write-Output "CONTAINER=$container"
    Write-Output "DATABASE=$database"
    Write-Output "TRANSCRIPT=$sessionPath"
    Write-Output "PYTEST_OUTPUT=$pytestPath"
    Write-Output 'DATA=synthetic only'
    Write-Output 'NETWORK=host port bound to 127.0.0.1 only; no volume mounts'
}
finally {
    $env:DATABASE_URL = $previousDatabaseUrl
    $env:M31_S02_T002_DISPOSABLE_TEST_DATABASE = $previousTaskGate
    $env:M31_S02_T002_DISPOSABLE_TEST_DATABASE_NAME = $previousTaskDatabase
    $env:M31_S02_T002_LEGACY_DEFINITION_ID = $previousLegacyId
    $env:M31_S02_T002_LEGACY_EVENT_CODE = $previousLegacyCode
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M31.S02.T002' -or $labels.'codex.disposable' -ne 'true') {
            throw "Cleanup refused: labels did not match the exact task-owned container $container"
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
    Stop-Transcript | Out-Null
}
