$ErrorActionPreference = 'Stop'

function Invoke-Docker {
    param([string[]]$Arguments)
    $output = @(& docker @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { throw "Docker command failed ($($Arguments -join ' ')): $($output -join ' ')" }
    return ($output -join "`n").Trim()
}

$image = 'postgres:16-alpine'
$user = 'fmcg_m31_s01_t001_test'
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 20)
$database = "fmcg_m31_s01_t001_$suffix"
$container = "codex-m31-s01-t001-$suffix"
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL
$previousTaskGate = $env:M31_S01_T001_DISPOSABLE_TEST_DATABASE
$previousTaskDatabase = $env:M31_S01_T001_DISPOSABLE_TEST_DATABASE_NAME
$transcriptPath = Join-Path $PSScriptRoot "postgres-test-run-$suffix.log"
$testOutputPath = Join-Path $PSScriptRoot "pytest-output-$suffix.log"
Start-Transcript -Path $transcriptPath -Force | Out-Null
try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Local PostgreSQL image ID was not returned.' }
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M31.S01.T001',
        '--label', 'codex.disposable=true', '--label', 'codex.database-purpose=M31-API-client-registry-tests',
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
        $env:M31_S01_T001_DISPOSABLE_TEST_DATABASE = '1'
        $env:M31_S01_T001_DISPOSABLE_TEST_DATABASE_NAME = $database
        $migrationOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        if ($LASTEXITCODE -ne 0) {
            $migrationOutput | Out-File -LiteralPath (Join-Path $PSScriptRoot 'migration-output.log') -Encoding utf8
            throw 'Fresh migration to head failed on the task-owned disposable database.'
        }
        $testOutput = @(& .\venv\Scripts\python.exe -m pytest -q --tb=short tests\test_m31_s01_t001_api_client_registry.py 2>&1)
        $testOutput | Out-File -LiteralPath $testOutputPath -Encoding utf8
        $testOutput
        if ($LASTEXITCODE -ne 0) { throw 'M31.S01.T001 API client registry checks failed.' }

        $downgradeOutput = @(& .\venv\Scripts\python.exe -m alembic downgrade 20261029_0041 2>&1)
        if ($LASTEXITCODE -ne 0) {
            $downgradeOutput | Out-File -LiteralPath (Join-Path $PSScriptRoot 'empty-registry-downgrade.log') -Encoding utf8
            throw 'Empty registry did not downgrade safely to its parent revision.'
        }
        $tableAbsent = Invoke-Docker @('exec', $container, 'psql', '-U', $user, '-d', $database, '-tAc', "SELECT to_regclass('public.api_client_applications') IS NULL")
        if ($tableAbsent -ne 't') { throw 'The empty-registry downgrade did not remove its table.' }

        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', 'CREATE TABLE api_client_applications (client_id UUID PRIMARY KEY)')
        $incompatibleOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        $incompatibleExitCode = $LASTEXITCODE
        $incompatibleOutput | Out-File -LiteralPath (Join-Path $PSScriptRoot 'migration-incompatible-shape.log') -Encoding utf8
        if ($incompatibleExitCode -eq 0 -or (($incompatibleOutput -join "`n") -notmatch 'Refusing to adopt incompatible')) {
            throw 'Migration did not fail closed on an incompatible pre-existing registry table.'
        }
        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', 'DROP TABLE api_client_applications')

        $compatibleWithoutTimestampDefaults = @'
CREATE TABLE api_client_applications (
    client_id UUID NOT NULL,
    owner_user_id UUID NOT NULL,
    name VARCHAR(160) NOT NULL,
    description TEXT NULL,
    environment VARCHAR(20) NOT NULL DEFAULT 'development',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_api_client_applications PRIMARY KEY (client_id),
    CONSTRAINT ck_api_client_applications_environment CHECK (environment IN ('development', 'sandbox', 'production')),
    CONSTRAINT uq_api_client_applications_owner_name_environment UNIQUE (owner_user_id, name, environment),
    CONSTRAINT fk_api_client_applications_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX ix_api_client_applications_owner_user_id ON api_client_applications (owner_user_id);
'@
        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', $compatibleWithoutTimestampDefaults)
        $defaultsOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        $defaultsExitCode = $LASTEXITCODE
        $defaultsOutput | Out-File -LiteralPath (Join-Path $PSScriptRoot 'migration-missing-defaults.log') -Encoding utf8
        if ($defaultsExitCode -eq 0 -or (($defaultsOutput -join "`n") -notmatch 'created_at server default')) {
            throw 'Migration did not reject an otherwise-compatible registry table without timestamp defaults.'
        }
        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', 'DROP TABLE api_client_applications')

        $weakenedEnvironmentCheck = $compatibleWithoutTimestampDefaults
        $weakenedEnvironmentCheck = $weakenedEnvironmentCheck.Replace('created_at TIMESTAMPTZ NOT NULL,', 'created_at TIMESTAMPTZ NOT NULL DEFAULT now(),')
        $weakenedEnvironmentCheck = $weakenedEnvironmentCheck.Replace('updated_at TIMESTAMPTZ NOT NULL,', 'updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),')
        $weakenedEnvironmentCheck = $weakenedEnvironmentCheck.Replace("CHECK (environment IN ('development', 'sandbox', 'production')),", "CHECK (environment IN ('development', 'sandbox', 'production') OR TRUE),")
        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', $weakenedEnvironmentCheck)
        $weakenedCheckOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        $weakenedCheckExitCode = $LASTEXITCODE
        $weakenedCheckOutput | Out-File -LiteralPath (Join-Path $PSScriptRoot 'migration-weakened-environment-check.log') -Encoding utf8
        if ($weakenedCheckExitCode -eq 0 -or (($weakenedCheckOutput -join "`n") -notmatch 'incompatible environment check')) {
            throw 'Migration did not reject a weakened environment constraint.'
        }
        $null = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-c', 'DROP TABLE api_client_applications')

        $creationOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        $creationOutput | Out-File -LiteralPath (Join-Path $PSScriptRoot 'migration-creation-path.log') -Encoding utf8
        if ($LASTEXITCODE -ne 0) {
            throw 'Migration did not create the registry table from revision 20261029_0041.'
        }
        & .\venv\Scripts\python.exe -m alembic current
        if ($LASTEXITCODE -ne 0) { throw 'Could not confirm the final migration revision.' }
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
    $env:M31_S01_T001_DISPOSABLE_TEST_DATABASE = $previousTaskGate
    $env:M31_S01_T001_DISPOSABLE_TEST_DATABASE_NAME = $previousTaskDatabase
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M31.S01.T001' -or $labels.'codex.disposable' -ne 'true') {
            throw "Cleanup refused: labels did not match the exact task-owned container $container"
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
    Stop-Transcript | Out-Null
}
