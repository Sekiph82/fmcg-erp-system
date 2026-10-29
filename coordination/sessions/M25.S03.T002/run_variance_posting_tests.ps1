$ErrorActionPreference = 'Stop'

function Invoke-Docker {
    param([string[]]$Arguments)
    $output = @(& docker @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { throw "Docker command failed ($($Arguments -join ' ')): $($output -join ' ')" }
    return ($output -join "`n").Trim()
}

$image = 'postgres:16-alpine'
$user = 'fmcg_m25_s03_t002_test'
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 20)
$database = "fmcg_m25_s03_t002_$suffix"
$container = "codex-m25-s03-t002-$suffix"
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL
$previousTaskGate = $env:M25_S03_T002_DISPOSABLE_TEST_DATABASE
$previousTaskDatabase = $env:M25_S03_T002_DISPOSABLE_TEST_DATABASE_NAME
$transcriptPath = Join-Path $PSScriptRoot 'postgres-test-run.log'
$testOutputPath = Join-Path $PSScriptRoot 'pytest-output.log'
Start-Transcript -Path $transcriptPath -Force | Out-Null
try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Local PostgreSQL image ID was not returned.' }
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M25.S03.T002',
        '--label', 'codex.disposable=true', '--label', 'codex.database-purpose=M25-landed-cost-variance-posting-tests',
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
        $env:M25_S03_T002_DISPOSABLE_TEST_DATABASE = '1'
        $env:M25_S03_T002_DISPOSABLE_TEST_DATABASE_NAME = $database
        $migrationOutput = @(& .\venv\Scripts\python.exe -m alembic upgrade head 2>&1)
        if ($LASTEXITCODE -ne 0) {
            $migrationOutput | Out-File -LiteralPath (Join-Path $PSScriptRoot 'migration-output.log') -Encoding utf8
            throw 'Fresh migration to head failed on the task-owned disposable database.'
        }
        $testOutput = @(& .\venv\Scripts\python.exe -m pytest -q --tb=short tests\test_m25_s03_t002_landed_cost_variance_posting.py 2>&1)
        $testOutput | Out-File -LiteralPath $testOutputPath -Encoding utf8
        $testOutput
        if ($LASTEXITCODE -ne 0) { throw 'M25.S03.T002 landed-cost variance posting database checks failed.' }
        & .\venv\Scripts\python.exe -m alembic current
        if ($LASTEXITCODE -ne 0) { throw 'Could not confirm the final migration revision.' }
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
    $env:M25_S03_T002_DISPOSABLE_TEST_DATABASE = $previousTaskGate
    $env:M25_S03_T002_DISPOSABLE_TEST_DATABASE_NAME = $previousTaskDatabase
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M25.S03.T002' -or $labels.'codex.disposable' -ne 'true') {
            throw "Cleanup refused: labels did not match the exact task-owned container $container"
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
    Stop-Transcript | Out-Null
}
