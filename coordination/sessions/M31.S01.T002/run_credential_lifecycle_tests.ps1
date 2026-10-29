# Native tools use stderr for normal Alembic/pytest progress; command exit codes
# are checked explicitly below and task-owned failures are raised as PowerShell
# exceptions after their output has been captured.
$ErrorActionPreference = 'Continue'

function Invoke-Docker {
    param([string[]]$Arguments)
    $output = @(& docker @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { throw "Docker command failed ($($Arguments -join ' ')): $($output -join ' ')" }
    return ($output -join "`n").Trim()
}

$image = 'postgres:16-alpine'
$user = 'fmcg_m31_s01_t002_test'
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 20)
$database = "fmcg_m31_s01_t002_$suffix"
$container = "codex-m31-s01-t002-$suffix"
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL
$previousTaskGate = $env:M31_S01_T002_DISPOSABLE_TEST_DATABASE
$previousTaskDatabase = $env:M31_S01_T002_DISPOSABLE_TEST_DATABASE_NAME
$transcriptPath = Join-Path $PSScriptRoot "postgres-test-run-$suffix.log"
$testOutputPath = Join-Path $PSScriptRoot "pytest-output-$suffix.log"
Start-Transcript -Path $transcriptPath -Force | Out-Null
try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Local PostgreSQL image ID was not returned.' }
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M31.S01.T002',
        '--label', 'codex.disposable=true', '--label', 'codex.database-purpose=M31-API-credential-lifecycle-tests',
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
        $env:M31_S01_T002_DISPOSABLE_TEST_DATABASE = '1'
        $env:M31_S01_T002_DISPOSABLE_TEST_DATABASE_NAME = $database
        $migrationOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        if ($LASTEXITCODE -ne 0) { throw "Fresh migration to head failed: $($migrationOutput -join ' ')" }
        $testOutput = @(& .\venv\Scripts\python.exe -m pytest -q --tb=short tests\test_m31_s01_t002_credential_lifecycle.py 2>&1)
        $testOutput | Out-File -LiteralPath $testOutputPath -Encoding utf8
        $testOutput
        if ($LASTEXITCODE -ne 0) { throw 'M31.S01.T002 API credential lifecycle checks failed.' }

        $downgradeOutput = @(& .\venv\Scripts\python.exe -m alembic downgrade 20261029_0042 2>&1)
        if ($LASTEXITCODE -ne 0) { throw "Empty credential lifecycle did not downgrade safely: $($downgradeOutput -join ' ')" }
        $removed = Invoke-Docker @('exec', $container, 'psql', '-U', $user, '-d', $database, '-tAc', "SELECT to_regclass('public.api_oauth_client_secrets') IS NULL AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='dev_api_keys' AND column_name='application_id')")
        if ($removed -ne 't') { throw 'Empty credential lifecycle downgrade left task schema behind.' }

        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', 'CREATE TABLE api_oauth_client_secrets (secret_id UUID PRIMARY KEY)')
        $incompatibleOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        $incompatibleExitCode = $LASTEXITCODE
        $incompatibleOutput | Out-File -LiteralPath (Join-Path $PSScriptRoot 'migration-incompatible-secret-shape.log') -Encoding utf8
        if ($incompatibleExitCode -eq 0 -or (($incompatibleOutput -join "`n") -notmatch 'Refusing to adopt incompatible api_oauth_client_secrets columns')) {
            throw 'Migration did not fail closed on an incompatible pre-existing OAuth secret table.'
        }
        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', 'DROP TABLE api_oauth_client_secrets')
        $creationOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        if ($LASTEXITCODE -ne 0) { throw "Migration did not recreate credential schema from 0042: $($creationOutput -join ' ')" }
        $current = (& .\venv\Scripts\python.exe -m alembic current 2>&1) -join "`n"
        if ($LASTEXITCODE -ne 0 -or $current -notmatch '20261029_0043') { throw "Could not confirm final migration revision: $current" }
    }
    finally { Pop-Location }

    Write-Output 'RESULT=PASS'
    Write-Output "POSTGRES_IMAGE=$image"
    Write-Output "POSTGRES_IMAGE_ID=$imageId"
    Write-Output "CONTAINER=$container"
    Write-Output "DATABASE=$database"
    Write-Output "TRANSCRIPT=$transcriptPath"
    Write-Output "PYTEST_OUTPUT=$testOutputPath"
    Write-Output 'DATA=synthetic only'
    Write-Output 'NETWORK=host port bound to 127.0.0.1 only; no volume mounts'
}
finally {
    $env:DATABASE_URL = $previousDatabaseUrl
    $env:M31_S01_T002_DISPOSABLE_TEST_DATABASE = $previousTaskGate
    $env:M31_S01_T002_DISPOSABLE_TEST_DATABASE_NAME = $previousTaskDatabase
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M31.S01.T002' -or $labels.'codex.disposable' -ne 'true') {
            throw "Cleanup refused: labels did not match the exact task-owned container $container"
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
    Stop-Transcript | Out-Null
}
