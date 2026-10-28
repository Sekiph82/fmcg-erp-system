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
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 20)
$database = "fmcg_m21_s03_t003_$suffix"
$container = "codex-m21-s03-t003-$suffix"
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL
$previousTaskGate = $env:M21_DISPOSABLE_TEST_DATABASE
$previousTaskDatabase = $env:M21_DISPOSABLE_TEST_DATABASE_NAME

try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Local PostgreSQL image ID was not returned.' }

    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M21.S03.T003',
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
        $env:M21_DISPOSABLE_TEST_DATABASE = '1'
        $env:M21_DISPOSABLE_TEST_DATABASE_NAME = $database

        & python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Alembic upgrade failed for the task-owned disposable database.' }
        & python -m pytest -q tests/test_m21_s03_t003_substitution_governance_db.py
        if ($LASTEXITCODE -ne 0) { throw 'Substitution governance PostgreSQL integration test failed.' }
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
    $env:M21_DISPOSABLE_TEST_DATABASE = $previousTaskGate
    $env:M21_DISPOSABLE_TEST_DATABASE_NAME = $previousTaskDatabase
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M21.S03.T003') {
            throw "Cleanup refused: container label did not match the exact task-owned container $container."
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
}
