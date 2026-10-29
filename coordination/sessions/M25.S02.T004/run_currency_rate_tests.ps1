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
$user = 'fmcg_m25_s02_t004_test'
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 20)
$database = "fmcg_m25_s02_t004_$suffix"
$container = "codex-m25-s02-t004-$suffix"
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL
$previousTaskGate = $env:M25_S02_T004_DISPOSABLE_TEST_DATABASE
$previousTaskDatabase = $env:M25_S02_T004_DISPOSABLE_TEST_DATABASE_NAME
try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Local PostgreSQL image ID was not returned.' }
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M25.S02.T004',
        '--label', 'codex.disposable=true', '--label', 'codex.database-purpose=M25-landed-cost-fx-tests',
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
        $env:M25_S02_T004_DISPOSABLE_TEST_DATABASE = '1'
        $env:M25_S02_T004_DISPOSABLE_TEST_DATABASE_NAME = $database

        & .\venv\Scripts\python.exe -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Alembic fresh-baseline upgrade failed.' }

        & .\venv\Scripts\python.exe -m alembic downgrade 20261029_0038
        if ($LASTEXITCODE -ne 0) { throw 'Clean downgrade to the pre-estimate/FX landed-cost schema failed.' }
        $baselineSnapshotSql = @"
ALTER TABLE lc_headers ADD COLUMN exchange_rate_id UUID NULL;
ALTER TABLE lc_headers ADD COLUMN exchange_rate_date DATE NULL;
ALTER TABLE lc_headers ADD COLUMN exchange_rate_source VARCHAR(20) NULL;
COMMENT ON COLUMN lc_headers.exchange_rate_id IS 'Added by Alembic revision 20261029_0040; exact finance rate row used for this snapshot';
COMMENT ON COLUMN lc_headers.exchange_rate_date IS 'Added by Alembic revision 20261029_0040; effective rate date, null for legacy unknowns';
COMMENT ON COLUMN lc_headers.exchange_rate_source IS 'Added by Alembic revision 20261029_0040; source copied with the rate snapshot';
ALTER TABLE lc_headers ADD CONSTRAINT fk_lc_headers_exchange_rate_id_exchange_rates FOREIGN KEY (exchange_rate_id) REFERENCES exchange_rates(id) ON DELETE SET NULL;
ALTER TABLE lc_lines ADD COLUMN exchange_rate_id UUID NULL;
ALTER TABLE lc_lines ADD COLUMN exchange_rate_date DATE NULL;
ALTER TABLE lc_lines ADD COLUMN exchange_rate_source VARCHAR(20) NULL;
COMMENT ON COLUMN lc_lines.exchange_rate_id IS 'Added by Alembic revision 20261029_0040; exact finance rate row used for this snapshot';
COMMENT ON COLUMN lc_lines.exchange_rate_date IS 'Added by Alembic revision 20261029_0040; effective rate date, null for legacy unknowns';
COMMENT ON COLUMN lc_lines.exchange_rate_source IS 'Added by Alembic revision 20261029_0040; source copied with the rate snapshot';
ALTER TABLE lc_lines ADD CONSTRAINT fk_lc_lines_exchange_rate_id_exchange_rates FOREIGN KEY (exchange_rate_id) REFERENCES exchange_rates(id) ON DELETE SET NULL;
"@
        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', $baselineSnapshotSql)
        $legacySql = @"
INSERT INTO lc_headers (id, lc_no, reference_type, currency_code, exchange_rate, total_lc_amount_fc, total_lc_amount_base, allocation_method, status)
VALUES ('25000000-0000-0000-0000-000000000038', 'LC-T004-LEGACY', 'MANUAL', 'USD', 1, 25.125, 25.125, 'BY_VALUE', 'DRAFT');
INSERT INTO lc_lines (id, header_id, cost_type, amount_fc, currency_code, exchange_rate, amount_base, is_included_in_valuation)
VALUES ('25000000-0000-0000-0000-000000000039', '25000000-0000-0000-0000-000000000038', 'FREIGHT_SEA', 25.125, 'USD', 1, 25.125, TRUE);
"@
        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', $legacySql)
        & .\venv\Scripts\python.exe -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Alembic did not backfill estimates and add landed-cost rate snapshots to legacy records.' }

        & .\venv\Scripts\python.exe -m pytest -q tests\test_m25_s02_t004_currency_rates.py
        if ($LASTEXITCODE -ne 0) { throw 'Landed-cost migration or dated exchange-rate checks failed.' }

        $downgradeOutput = @(& .\venv\Scripts\python.exe -m alembic downgrade 20261029_0039 2>&1)
        $downgradeExitCode = $LASTEXITCODE
        $downgradeText = $downgradeOutput -join "`n"
        if ($downgradeExitCode -eq 0 -or $downgradeText -notmatch 'Refusing to discard saved Finance rate links') {
            throw 'Downgrade did not refuse to discard saved exchange-rate provenance.'
        }
        Write-Output 'DOWNGRADE_WITH_SAVED_RATE=SAFELY_REFUSED'
        & .\venv\Scripts\python.exe -m alembic current
        if ($LASTEXITCODE -ne 0) { throw 'Could not confirm migration head after the expected guarded downgrade refusal.' }
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
    $env:M25_S02_T004_DISPOSABLE_TEST_DATABASE = $previousTaskGate
    $env:M25_S02_T004_DISPOSABLE_TEST_DATABASE_NAME = $previousTaskDatabase
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M25.S02.T004' -or $labels.'codex.disposable' -ne 'true') {
            throw "Cleanup refused: labels did not match the exact task-owned container $container"
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
}
