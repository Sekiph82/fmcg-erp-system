$ErrorActionPreference = 'Stop'

function Invoke-Docker {
    param([string[]]$Arguments)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = @(& docker @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
    if ($exitCode -ne 0) { throw "Docker command failed ($($Arguments -join ' ')): $($output -join ' ')" }
    return ($output -join "`n").Trim()
}

$image = 'postgres:16-alpine'
$user = 'fmcg_m25_s02_t003_test'
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 20)
$database = "fmcg_m25_s02_t003_$suffix"
$container = "codex-m25-s02-t003-$suffix"
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL
$previousTaskGate = $env:M25_S02_T003_DISPOSABLE_TEST_DATABASE
$previousTaskDatabase = $env:M25_S02_T003_DISPOSABLE_TEST_DATABASE_NAME

try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Local PostgreSQL image ID was not returned.' }
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M25.S02.T003',
        '--label', 'codex.disposable=true', '--label', 'codex.database-purpose=M25-landed-cost-actual-tests',
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
    if ($binding -notmatch '^127\.0\.0\.1:(\d+)$') { throw "Database port was not loopback-only: $binding" }
    $port = $Matches[1]
    $backend = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\backend'))
    Push-Location $backend
    try {
        $env:DATABASE_URL = "postgresql+asyncpg://$user@127.0.0.1:$port/$database"
        $env:M25_S02_T003_DISPOSABLE_TEST_DATABASE = '1'
        $env:M25_S02_T003_DISPOSABLE_TEST_DATABASE_NAME = $database
        & .\venv\Scripts\python.exe -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Alembic failed to adopt the fresh baseline landed-cost actual schema.' }
        & .\venv\Scripts\python.exe -m alembic downgrade 20261029_0038
        if ($LASTEXITCODE -ne 0) { throw 'Safe downgrade to the pre-T003 revision failed.' }

        $legacySql = @"
INSERT INTO lc_headers (id, lc_no, reference_type, currency_code, exchange_rate, total_lc_amount_fc, total_lc_amount_base, allocation_method, status)
VALUES ('25000000-0000-0000-0000-000000000038', 'LC-T003-LEGACY', 'MANUAL', 'USD', 1, 25.125, 25.125, 'BY_VALUE', 'DRAFT');
INSERT INTO lc_lines (id, header_id, cost_type, amount_fc, currency_code, exchange_rate, amount_base, is_included_in_valuation)
VALUES ('25000000-0000-0000-0000-000000000039', '25000000-0000-0000-0000-000000000038', 'FREIGHT_SEA', 25.125, 'USD', 1, 25.125, TRUE);
DROP TABLE IF EXISTS lc_line_actuals;
ALTER TABLE lc_lines DROP COLUMN IF EXISTS estimated_amount_fc;
"@
        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', $legacySql)

        & .\venv\Scripts\python.exe -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Alembic upgrade to head failed for the task-owned disposable database.' }
        & .\venv\Scripts\python.exe -m pytest -q tests\test_m25_s02_t003_landed_cost_actuals.py
        if ($LASTEXITCODE -ne 0) { throw 'Landed-cost estimated/actual tests failed.' }
    }
    finally { Pop-Location }

    Write-Output 'RESULT=PASS'
    Write-Output "POSTGRES_IMAGE=$image"
    Write-Output "POSTGRES_IMAGE_ID=$imageId"
    Write-Output "CONTAINER=$container"
    Write-Output "DATABASE=$database"
    Write-Output 'DATA=synthetic only'
    Write-Output 'NETWORK=host port bound to 127.0.0.1 only; no volume mounts'
}
finally {
    $env:DATABASE_URL = $previousDatabaseUrl
    $env:M25_S02_T003_DISPOSABLE_TEST_DATABASE = $previousTaskGate
    $env:M25_S02_T003_DISPOSABLE_TEST_DATABASE_NAME = $previousTaskDatabase
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M25.S02.T003' -or $labels.'codex.disposable' -ne 'true') {
            throw "Cleanup refused: labels did not match the exact task-owned container $container"
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
}
