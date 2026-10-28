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
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 16)
$container = "fmcg_m21_s05_t001_$suffix"
$dbSuites = @(
    @{ Prefix = 'fmcg_m21_s01_t002'; Files = @('tests/test_m21_s01_t002_density_uom.py', 'tests/test_m21_s01_t002_conversion_db.py') },
    @{ Prefix = 'fmcg_m21_s01_t003'; Files = @('tests/test_m21_s01_t003_package_components.py', 'tests/test_m21_s01_t003_package_components_db.py') },
    @{ Prefix = 'fmcg_m21_s01_t004'; Files = @('tests/test_m21_s01_t004_profile_versions.py', 'tests/test_m21_s01_t004_profile_versions_db.py', 'tests/test_m21_s01_t001_conversion_profile_model.py') },
    @{ Prefix = 'fmcg_m21_s02_t001'; Files = @('tests/test_m21_s02_t001_expected_yield.py', 'tests/test_m21_s02_t001_expected_yield_db.py') },
    @{ Prefix = 'fmcg_m21_s02_t002'; Files = @('tests/test_m21_s02_t002_loss_categories.py', 'tests/test_m21_s02_t002_loss_categories_db.py') },
    @{ Prefix = 'fmcg_m21_s02_t003'; Files = @('tests/test_waste_recipe_standard_loss.py', 'tests/test_waste_recipe_standard_loss_db.py') }
)
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL
$previousTaskGate = $env:M21_DISPOSABLE_TEST_DATABASE
$previousTaskDatabase = $env:M21_DISPOSABLE_TEST_DATABASE_NAME

try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Local PostgreSQL image ID was not returned.' }

    $firstDatabase = "$($dbSuites[0].Prefix)_$suffix"
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M21.S05.T001',
        '--publish', '127.0.0.1::5432',
        '--env', "POSTGRES_USER=$user", '--env', "POSTGRES_DB=$firstDatabase",
        '--env', 'POSTGRES_HOST_AUTH_METHOD=trust', $image
    )
    $started = $true

    $ready = $false
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        & docker exec $container pg_isready -U $user -d $firstDatabase *> $null
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
        for ($index = 0; $index -lt $dbSuites.Count; $index++) {
            $suite = $dbSuites[$index]
            $database = "$($suite.Prefix)_$suffix"
            if ($index -gt 0) {
                $null = Invoke-Docker @('exec', $container, 'createdb', '-U', $user, '-O', $user, $database)
            }

            $env:DATABASE_URL = "postgresql+asyncpg://$user@127.0.0.1:$port/$database"
            $env:M21_DISPOSABLE_TEST_DATABASE = '1'
            $env:M21_DISPOSABLE_TEST_DATABASE_NAME = $database

            & python -m alembic upgrade head
            if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade failed for $database." }
            & python -m pytest -q @($suite.Files)
            if ($LASTEXITCODE -ne 0) { throw "Focused tests failed for $database." }
        }

        $env:DATABASE_URL = $null
        $env:M21_DISPOSABLE_TEST_DATABASE = $null
        $env:M21_DISPOSABLE_TEST_DATABASE_NAME = $null
        & python -m pytest -q tests/test_m21_s04_t001_conversion_api_contract.py tests/test_production_cost_yield_variance.py
        if ($LASTEXITCODE -ne 0) { throw 'Conversion API contract or yield-cost variance unit tests failed.' }
    }
    finally { Pop-Location }

    Write-Output 'RESULT=PASS'
    Write-Output "POSTGRES_IMAGE=$image"
    Write-Output "POSTGRES_IMAGE_ID=$imageId"
    Write-Output "CONTAINER=$container"
    Write-Output 'DATABASES=6 task-owned ephemeral databases; synthetic data only'
    Write-Output 'NETWORK=host port bound to 127.0.0.1 only; no volume mounts'
}
finally {
    $env:DATABASE_URL = $previousDatabaseUrl
    $env:M21_DISPOSABLE_TEST_DATABASE = $previousTaskGate
    $env:M21_DISPOSABLE_TEST_DATABASE_NAME = $previousTaskDatabase
    if ($started) {
        $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M21.S05.T001') {
            throw "Cleanup refused: container label did not match the exact task-owned container $container."
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
}
