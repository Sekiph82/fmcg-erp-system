param(
    [string[]]$OnlyModules = @()
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$runId = [Guid]::NewGuid().ToString('N').Substring(0,24)
$container = "fmcg-m24-t004-$runId"
$template = "fmcg_m24_s04_t004_$runId"
$runKind = if ($OnlyModules.Count -gt 0) { 'focused' } else { 'acceptance' }
$log = Join-Path $PSScriptRoot "t004-postgres-$runKind-$runId.log"
$modules = @(
    @{ file='test_m24_s01_t001_material_reservation_db.py'; task='M24_S01_T001' },
    @{ file='test_m24_s02_t001_material_issue_db.py'; task='M24_S02_T001' },
    @{ file='test_m24_s02_t002_actual_consumption_db.py'; task='M24_S02_T002' },
    @{ file='test_m24_s02_t003_material_return_db.py'; task='M24_S02_T003' },
    @{ file='test_m24_s02_t004_material_scrap_db.py'; task='M24_S02_T004' },
    @{ file='test_m24_s03_t001_wip_location_db.py'; task='M24_S03_T001' },
    @{ file='test_m24_s03_t002_bulk_transfer_db.py'; task='M24_S03_T002' },
    @{ file='test_m24_s03_t003_finished_goods_receipt_db.py'; task='M24_S03_T003' },
    @{ file='test_m24_s03_t004_packaging_genealogy_db.py'; task='M24_S03_T004' },
    @{ file='test_m24_s04_t001_atomic_posting_db.py'; task='M24_S04_T001' },
    @{ file='test_m24_s04_t002_genealogy_db.py'; task='M24_S04_T002' },
    @{ file='test_m24_s04_t003_reversal_guards_db.py'; task='M24_S04_T003' },
    @{ file='test_m05_s03_t002_transaction_integrity_db.py'; task='M05_S03_T002' },
    @{ file='test_m05_s03_t003_stock_concurrency_db.py'; task='M05_S03_T003' },
    @{ file='test_m08_s03_t001_transition_guards_db.py'; task='M08_S03_T001' },
    @{ file='test_m08_s03_t002_production_inventory_atomicity_db.py'; task='M08_S03_T002' }
)
if ($OnlyModules.Count -gt 0) {
    $unknown = @($OnlyModules | Where-Object { $_ -notin $modules.file })
    if ($unknown.Count) { throw "Unknown M24 module(s): $($unknown -join ', ')" }
    $modules = @($modules | Where-Object { $_.file -in $OnlyModules })
}
@(
    'M24.S04.T004 disposable PostgreSQL acceptance run'
    "created=$(Get-Date -Format o)"
    "container=$container"
    "template_database=$template"
    'image=postgres:16.6'
    'host_bind=127.0.0.1 ephemeral port'
    'password=none'
    "modules=$($modules.file -join ',')"
) | Set-Content -LiteralPath $log -Encoding utf8
$failures = [System.Collections.Generic.List[string]]::new()
$runExit = 1
try {
    $created = docker run -d --rm --name $container `
        -e "POSTGRES_DB=$template" `
        -e 'POSTGRES_HOST_AUTH_METHOD=trust' `
        -p '127.0.0.1::5432' postgres:16.6 2>&1
    $created | Add-Content -LiteralPath $log -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw 'Could not start task-owned PostgreSQL container' }
    $port = $null
    for ($i = 0; $i -lt 60; $i++) {
        $published = docker port $container 5432/tcp 2>$null
        if ($LASTEXITCODE -eq 0 -and $published -match '127\.0\.0\.1:(\d+)') {
            $port = [int]$Matches[1]
            docker exec $container pg_isready -U postgres -d $template *> $null
            if ($LASTEXITCODE -eq 0) { break }
        }
        Start-Sleep -Seconds 1
    }
    if (-not $port) { throw 'Task-owned PostgreSQL did not become ready on a loopback port' }
    "host_port=$port" | Add-Content -LiteralPath $log -Encoding utf8
    Push-Location (Join-Path $repoRoot 'backend')
    try {
        $env:PYTHONPATH = 'tests;.'
        $env:DATABASE_URL = "postgresql+asyncpg://postgres@127.0.0.1:$port/$template"
        $migration = & .\venv\Scripts\python.exe -m alembic upgrade head 2>&1
        $migrationExit = $LASTEXITCODE
        "=== fresh migration exit=$migrationExit ===" | Add-Content -LiteralPath $log -Encoding utf8
        $migration | Add-Content -LiteralPath $log -Encoding utf8
        if ($migrationExit -ne 0) { throw "Fresh Alembic migration failed: $migrationExit" }
        $current = & .\venv\Scripts\python.exe -m alembic current 2>&1
        "=== migration current ===" | Add-Content -LiteralPath $log -Encoding utf8
        $current | Add-Content -LiteralPath $log -Encoding utf8
        foreach ($module in $modules) {
            $taskDbPrefix = $module.task.ToLowerInvariant()
            $database = "fmcg_$($taskDbPrefix)_$runId"
            if ($database -notmatch '^fmcg_m\d{2}_s\d{2}_t\d{3}_[a-f0-9]{24}$') {
                throw "Refusing unsafe database name: $database"
            }
            $clone = docker exec $container psql -U postgres -d postgres -v ON_ERROR_STOP=1 `
                -c "CREATE DATABASE $database WITH TEMPLATE $template" 2>&1
            if ($LASTEXITCODE -ne 0) { throw "Could not create disposable task database $database : $clone" }
            $env:DATABASE_URL = "postgresql+asyncpg://postgres@127.0.0.1:$port/$database"
            $flag = "$($module.task)_DISPOSABLE_TEST_DATABASE"
            Set-Item -Path "Env:$flag" -Value '1'
            Set-Item -Path "Env:${flag}_NAME" -Value $database
            "=== $($module.file) / $database ===" | Add-Content -LiteralPath $log -Encoding utf8
            $output = & .\venv\Scripts\python.exe -m pytest -q "tests/$($module.file)" 2>&1
            $testExit = $LASTEXITCODE
            $output | Add-Content -LiteralPath $log -Encoding utf8
            "PYTEST_EXIT=$testExit" | Add-Content -LiteralPath $log -Encoding utf8
            Remove-Item "Env:$flag" -ErrorAction SilentlyContinue
            Remove-Item "Env:${flag}_NAME" -ErrorAction SilentlyContinue
            if ($testExit -ne 0) {
                $failures.Add("$($module.file): pytest exit $testExit")
                Write-Output "$($module.file): FAIL"
            } else {
                Write-Output "$($module.file): PASS"
            }
        }
    } finally {
        Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        foreach ($module in $modules) {
            $flag = "$($module.task)_DISPOSABLE_TEST_DATABASE"
            Remove-Item "Env:$flag" -ErrorAction SilentlyContinue
            Remove-Item "Env:${flag}_NAME" -ErrorAction SilentlyContinue
        }
        Pop-Location
    }
    if ($failures.Count -eq 0) { $runExit = 0 }
    else { $failures | Add-Content -LiteralPath $log -Encoding utf8 }
} catch {
    "runner_error=$_" | Add-Content -LiteralPath $log -Encoding utf8
    Write-Output "runner_error=$_"
} finally {
    $removed = docker rm -f $container 2>&1
    if ($LASTEXITCODE -eq 0) {
        $remaining = docker ps -a --filter "name=^/$container$" --format '{{.Names}}'
        "cleanup_removed=$container`ncleanup_verified_absent=$(-not $remaining)" | Add-Content -LiteralPath $log -Encoding utf8
        if ($remaining) {
            'cleanup_verification=FAIL' | Add-Content -LiteralPath $log -Encoding utf8
            $runExit = 1
        }
    } else {
        "cleanup_error=$removed" | Add-Content -LiteralPath $log -Encoding utf8
        $runExit = 1
    }
}
if ($runExit -eq 0) {
    'RESULT=PASS' | Add-Content -LiteralPath $log -Encoding utf8
    Write-Output "LOG=$log"
    Write-Output 'RESULT=PASS'
} else {
    'RESULT=FAIL' | Add-Content -LiteralPath $log -Encoding utf8
    Write-Output "LOG=$log"
    Write-Output 'RESULT=FAIL'
}
exit $runExit
