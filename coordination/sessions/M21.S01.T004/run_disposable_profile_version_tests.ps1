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
    if ($exitCode -ne 0) {
        throw "Docker command failed ($($Arguments -join ' ')): $($output -join ' ')"
    }
    return ($output -join "`n").Trim()
}

$image = 'postgres:16-alpine'
$user = 'fmcg_m21_test'
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 24)
$container = "fmcg_m21_s01_t004_$suffix"
$database = "fmcg_m21_s01_t004_$suffix"
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL
$previousTaskGate = $env:M21_DISPOSABLE_TEST_DATABASE
$previousTaskDatabase = $env:M21_DISPOSABLE_TEST_DATABASE_NAME

try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Local PostgreSQL image ID was not returned.' }
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M21.S01.T004',
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
    $env:DATABASE_URL = "postgresql+asyncpg://$user@127.0.0.1:$port/$database"
    $env:M21_DISPOSABLE_TEST_DATABASE = '1'
    $env:M21_DISPOSABLE_TEST_DATABASE_NAME = $database

    $backend = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\backend'))
    $python = Join-Path $backend 'venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Project backend virtual-environment Python is unavailable.' }
    Push-Location $backend
    try {
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Alembic upgrade failed against the task-owned disposable database.' }
        & $python -m pytest -q tests/test_m21_s01_t004_profile_versions.py tests/test_m21_s01_t004_profile_versions_db.py tests/test_m21_s01_t001_conversion_profile_model.py
        if ($LASTEXITCODE -ne 0) { throw 'M21.S01.T004 focused profile version tests failed.' }
        $migration = Invoke-Docker @('exec', $container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $user, '-d', $database, '-q', '-t', '-A', '-c', 'SELECT string_agg(version_num, '','' ORDER BY version_num) FROM alembic_version')
    }
    finally { Pop-Location }

    Write-Output 'RESULT=PASS'
    Write-Output "POSTGRES_IMAGE=$image"
    Write-Output "POSTGRES_IMAGE_ID=$imageId"
    Write-Output "DATABASE=$database"
    Write-Output "MIGRATION_STATE=$migration"
    Write-Output 'NETWORK=host port bound to 127.0.0.1 only; no volume mounts'
    Write-Output 'DATA=synthetic conversion profile versions only'
}
finally {
    $env:DATABASE_URL = $previousDatabaseUrl
    $env:M21_DISPOSABLE_TEST_DATABASE = $previousTaskGate
    $env:M21_DISPOSABLE_TEST_DATABASE_NAME = $previousTaskDatabase
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M21.S01.T004') {
            throw "Cleanup refused: container label did not match the exact task-owned container $container."
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
}
