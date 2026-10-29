$ErrorActionPreference = 'Stop'
function Invoke-Docker {
    param([string[]]$Arguments)
    $output = @(& docker @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { throw "Docker command failed ($($Arguments -join ' ')): $($output -join ' ')" }
    return ($output -join "`n").Trim()
}
$cases = @(
    @{ task='M05.S03.T002'; env='M05_S03_T002_DISPOSABLE_TEST_DATABASE'; dbEnv='M05_S03_T002_DISPOSABLE_TEST_DATABASE_NAME'; prefix='fmcg_m05_s03_t002_'; file='test_m05_s03_t002_transaction_integrity_db.py' },
    @{ task='M05.S03.T003'; env='M05_S03_T003_DISPOSABLE_TEST_DATABASE'; dbEnv='M05_S03_T003_DISPOSABLE_TEST_DATABASE_NAME'; prefix='fmcg_m05_s03_t003_'; file='test_m05_s03_t003_stock_concurrency_db.py' },
    @{ task='M06.S03.T001'; env='M06_S03_T001_DISPOSABLE_TEST_DATABASE'; dbEnv='M06_S03_T001_DISPOSABLE_TEST_DATABASE_NAME'; prefix='fmcg_m06_s03_t001_'; file='test_m06_s03_t001_three_way_match_db.py' }
)
$image = 'postgres:16-alpine'
$imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
$envNames = @('DATABASE_URL') + @($cases | ForEach-Object { $_.env; $_.dbEnv })
$oldEnv = @{}
foreach ($name in $envNames) { $oldEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$transcript = Join-Path $PSScriptRoot 'receipt-regressions-final.log'
Start-Transcript -Path $transcript -Force | Out-Null
try {
    foreach ($case in $cases) {
        $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 20)
        $database = "$($case.prefix)$suffix"
        $container = "codex-m25-s03-t001-reg-$suffix"
        $user = 'fmcg_regression_test'
        $started = $false
        try {
            $null = Invoke-Docker @(
                'run', '--detach', '--rm', '--pull=never', '--name', $container,
                '--restart=no', '--label', 'codex.task=M25.S03.T001',
                '--label', "codex.regression-target=$($case.task)", '--label', 'codex.disposable=true',
                '--publish', '127.0.0.1::5432', '--env', "POSTGRES_USER=$user",
                '--env', "POSTGRES_DB=$database", '--env', 'POSTGRES_HOST_AUTH_METHOD=trust', $image
            )
            $started = $true
            $ready = $false
            for ($attempt = 0; $attempt -lt 90; $attempt++) {
                & docker exec $container pg_isready -U $user -d $database *> $null
                if ($LASTEXITCODE -eq 0) { $ready = $true; break }
                Start-Sleep -Seconds 1
            }
            if (-not $ready) { throw "Disposable database for $($case.task) did not become ready." }
            $binding = Invoke-Docker @('port', $container, '5432/tcp')
            if ($binding -notmatch '^127\.0\.0\.1:(\d+)$') { throw "Regression database port was not loopback-only: $binding" }
            $port = $Matches[1]
            $backend = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\backend'))
            Push-Location $backend
            try {
                $env:DATABASE_URL = "postgresql+asyncpg://$user@127.0.0.1:$port/$database"
                [Environment]::SetEnvironmentVariable($case.env, '1', 'Process')
                [Environment]::SetEnvironmentVariable($case.dbEnv, $database, 'Process')
                & .\venv\Scripts\python.exe -m alembic upgrade head
                if ($LASTEXITCODE -ne 0) { throw "Fresh migration failed for $($case.task)." }
                & .\venv\Scripts\python.exe -m pytest -q --tb=short "tests\$($case.file)"
                if ($LASTEXITCODE -ne 0) { throw "Receipt regression suite failed for $($case.task)." }
            }
            finally { Pop-Location }
            Write-Output "SUITE_PASS=$($case.task)"
            Write-Output "DATABASE=$database"
            Write-Output 'DATA=synthetic only'
            Write-Output 'NETWORK=loopback only; no volume mounts'
        }
        finally {
            [Environment]::SetEnvironmentVariable($case.env, $oldEnv[$case.env], 'Process')
            [Environment]::SetEnvironmentVariable($case.dbEnv, $oldEnv[$case.dbEnv], 'Process')
            if ($started) {
                $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
                $labels = $labelsJson | ConvertFrom-Json
                if ($labels.'codex.task' -ne 'M25.S03.T001' -or $labels.'codex.regression-target' -ne $case.task -or $labels.'codex.disposable' -ne 'true') {
                    throw "Cleanup refused for non-matching regression container $container."
                }
                $null = Invoke-Docker @('stop', $container)
                $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
                if ($remaining) { throw "Regression container remains after cleanup: $container" }
            }
        }
    }
    Write-Output 'REGRESSION_RESULT=PASS'
}
finally {
    foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $oldEnv[$name], 'Process') }
    Stop-Transcript | Out-Null
}
