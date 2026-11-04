$ErrorActionPreference = "Stop"
$sessionDir = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $sessionDir "..\..\..")).Path
$suffix = [Guid]::NewGuid().ToString("N").Substring(0, 24)
$databaseName = "fmcg_m34_s04_t004_$suffix"
$containerName = "fmcg-m34-s04-t004-$suffix"
$runLog = Join-Path $sessionDir "disposable-postgres-run-V12.log"
$cleanupLog = Join-Path $sessionDir "container-cleanup-V12.log"
$testExitCode = 1
@(
    "database=$databaseName"
    "container=$containerName"
    "image=postgres:16.6"
    "host_bind=127.0.0.1"
    "password=none"
) | Set-Content -Path $runLog -Encoding utf8

try {
    Write-Output "database=$databaseName"
    Write-Output "container=$containerName"
    Write-Output "image=postgres:16.6"
    Write-Output "host_bind=127.0.0.1"
    Write-Output "password=none"

    $dockerOutput = docker run -d --rm --name $containerName `
        -e "POSTGRES_DB=$databaseName" `
        -e "POSTGRES_HOST_AUTH_METHOD=trust" `
        -p "127.0.0.1::5432" postgres:16.6
    $dockerOutput | Add-Content -Path $runLog -Encoding utf8
    $dockerOutput | Write-Output
    if ($LASTEXITCODE -ne 0) { throw "Docker failed to start the task-owned PostgreSQL container" }

    $hostPort = $null
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        $published = docker port $containerName 5432/tcp 2>$null
        if ($LASTEXITCODE -eq 0 -and $published -match "127\.0\.0\.1:(\d+)") {
            $hostPort = [int]$Matches[1]
            $ready = docker exec $containerName pg_isready -U postgres -d $databaseName 2>$null
            if ($LASTEXITCODE -eq 0) { break }
        }
        Start-Sleep -Seconds 1
    }
    if (-not $hostPort) { throw "Task-owned PostgreSQL did not become ready on a loopback port" }
    Write-Output "host_port=$hostPort"

    Push-Location (Join-Path $repoRoot "backend")
    try {
        $env:DATABASE_URL = "postgresql+asyncpg://postgres@127.0.0.1:$hostPort/$databaseName"
        $env:M34_S04_T004_DISPOSABLE_TEST_DATABASE = "1"
        $env:M34_S04_T004_DISPOSABLE_TEST_DATABASE_NAME = $databaseName
        $migrationOutput = & .\venv\Scripts\python.exe -m alembic upgrade head 2>&1
        $migrationExitCode = $LASTEXITCODE
        $migrationOutput | Add-Content -Path $runLog -Encoding utf8
        $migrationOutput | Write-Output
        if ($migrationExitCode -ne 0) { throw "Alembic upgrade failed with exit code $migrationExitCode" }
        $pytestOutput = & .\venv\Scripts\python.exe -m pytest -q tests/test_m34_s04_t004_purchase_invoice_posting_db.py 2>&1
        $testExitCode = $LASTEXITCODE
        $pytestOutput | Add-Content -Path $runLog -Encoding utf8
        $pytestOutput | Write-Output
    } finally {
        Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
        Remove-Item Env:M34_S04_T004_DISPOSABLE_TEST_DATABASE -ErrorAction SilentlyContinue
        Remove-Item Env:M34_S04_T004_DISPOSABLE_TEST_DATABASE_NAME -ErrorAction SilentlyContinue
        Pop-Location
    }
} catch {
    "runner_error=$_" | Add-Content -Path $runLog -Encoding utf8
    Write-Error $_
    $testExitCode = 1
} finally {
    $removed = docker rm -f $containerName 2>&1
    if ($LASTEXITCODE -eq 0) {
        $remaining = docker ps -a --filter "name=^/$containerName$" --format "{{.Names}}"
        "removed=$containerName`nverified_absent=$(-not $remaining)" |
            Set-Content -Path $cleanupLog -Encoding utf8
    } else {
        "remove_output=$removed`ninspect_output=$(docker inspect $containerName 2>&1)" |
            Set-Content -Path $cleanupLog -Encoding utf8
        $testExitCode = 1
    }
}

exit $testExitCode
