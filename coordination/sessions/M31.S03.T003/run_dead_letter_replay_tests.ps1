$ErrorActionPreference = 'Stop'

function Invoke-Docker {
    param([string[]]$Arguments)
    $output = @(& docker @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed ($($Arguments -join ' ')): $($output -join ' ')" }
    return ($output -join "`n").Trim()
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$backendRoot = Join-Path $repoRoot 'backend'
$image = 'postgres:16-alpine'
$suffix = [guid]::NewGuid().ToString('N').Substring(0, 24)
$database = "fmcg_m31_s03_t003_$suffix"
$container = "codex-m31-s03-t003-$suffix"
$started = $false
$previousUrl = $env:DATABASE_URL
$previousGate = $env:M31_S03_T003_DISPOSABLE_TEST_DATABASE
$previousName = $env:M31_S03_T003_DISPOSABLE_TEST_DATABASE_NAME

try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Expected local PostgreSQL image ID was not returned.' }
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--name', $container,
        '--label', 'codex.task=M31.S03.T003',
        '--label', 'codex.disposable=true',
        '--label', 'codex.database-purpose=M31-dead-letter-replay-tests',
        '--restart=no', '--publish', '127.0.0.1::5432',
        '--env', 'POSTGRES_USER=postgres', '--env', "POSTGRES_DB=$database",
        '--env', 'POSTGRES_HOST_AUTH_METHOD=trust', $image
    )
    $started = $true
    $portMapping = $null
    for ($attempt = 0; $attempt -lt 90 -and -not $portMapping; $attempt++) {
        Start-Sleep -Milliseconds 500
        $portMapping = Invoke-Docker @('port', $container, '5432/tcp')
    }
    if (-not $portMapping) { throw 'Disposable PostgreSQL did not publish a loopback port.' }
    $port = ($portMapping -split ':')[-1]
    $ready = $false
    for ($attempt = 0; $attempt -lt 90 -and -not $ready; $attempt++) {
        $null = & docker exec $container pg_isready -U postgres -d $database 2>$null
        $ready = $LASTEXITCODE -eq 0
        if (-not $ready) { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'Disposable PostgreSQL did not become ready.' }

    $env:DATABASE_URL = "postgresql+asyncpg://postgres@127.0.0.1:$port/$database"
    $env:M31_S03_T003_DISPOSABLE_TEST_DATABASE = '1'
    $env:M31_S03_T003_DISPOSABLE_TEST_DATABASE_NAME = $database
    Push-Location $backendRoot
    try {
        $migrationOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        if ($LASTEXITCODE -ne 0) { throw "Disposable migration failed: $($migrationOutput -join ' ')" }
        & .\venv\Scripts\python.exe -m pytest -vv -s tests\test_m31_s03_t003_dead_letter_replay_db.py
        if ($LASTEXITCODE -ne 0) { throw 'M31.S03.T003 disposable PostgreSQL tests failed.' }
        $current = (& .\venv\Scripts\python.exe -m alembic current 2>&1) -join "`n"
        if ($LASTEXITCODE -ne 0 -or $current -notmatch '20261030_0003') {
            throw "Could not confirm the T003 migration head: $current"
        }
    }
    finally { Pop-Location }
    Write-Output 'RESULT=PASS'
    Write-Output "DATABASE=$database"
    Write-Output "POSTGRES_IMAGE_ID=$imageId"
    Write-Output "MIGRATION=$current"
}
finally {
    $env:DATABASE_URL = $previousUrl
    $env:M31_S03_T003_DISPOSABLE_TEST_DATABASE = $previousGate
    $env:M31_S03_T003_DISPOSABLE_TEST_DATABASE_NAME = $previousName
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M31.S03.T003' -or $labels.'codex.disposable' -ne 'true' -or
            $labels.'codex.database-purpose' -ne 'M31-dead-letter-replay-tests') {
            throw "Cleanup refused because labels did not match this exact task container: $container"
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned PostgreSQL container remains: $container" }
    }
}
