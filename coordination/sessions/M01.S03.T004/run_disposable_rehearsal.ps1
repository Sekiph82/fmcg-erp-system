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

function Invoke-Query {
    param([string]$Container, [string]$User, [string]$Database, [string]$Sql)
    return Invoke-Docker @('exec', $Container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $User, '-d', $Database, '-q', '-t', '-A', '-c', $Sql)
}

function Assert-Equal {
    param([string]$Name, [string]$Expected, [string]$Actual)
    if ($Expected -cne $Actual) {
        throw "$Name mismatch: expected '$Expected', got '$Actual'"
    }
}

$image = 'postgres:16-alpine'
$user = 'fmcg_rehearsal'
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 10)
$container = "fmcg_m01_t004_$suffix"
$sourceDb = "t004_src_$suffix"
$restoreDb = "t004_restore_$suffix"
$started = $false
$previousDatabaseUrl = $env:DATABASE_URL

try {
    $imageId = Invoke-Docker @('image', 'inspect', '--format', '{{.Id}}', $image)
    if (-not $imageId.StartsWith('sha256:')) { throw 'Pinned local image ID was not returned.' }
    $null = Invoke-Docker @(
        'run', '--detach', '--rm', '--pull=never', '--name', $container,
        '--restart=no', '--label', 'codex.task=M01.S03.T004',
        '--publish', '127.0.0.1::5432',
        '--env', "POSTGRES_USER=$user", '--env', "POSTGRES_DB=$sourceDb",
        '--env', 'POSTGRES_HOST_AUTH_METHOD=trust', $image
    )
    $started = $true

    $ready = $false
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        & docker exec $container pg_isready -U $user -d $sourceDb *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Disposable PostgreSQL did not become ready within 90 seconds.' }

    $binding = Invoke-Docker @('port', $container, '5432/tcp')
    if ($binding -notmatch '^127\.0\.0\.1:(\d+)$') { throw "Database port was not loopback-only: $binding" }
    $port = $Matches[1]

    $python = Join-Path $PSScriptRoot '..\..\..\backend\venv\Scripts\python.exe'
    $python = [System.IO.Path]::GetFullPath($python)
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Project backend virtual-environment Python is unavailable.' }
    $env:DATABASE_URL = "postgresql+asyncpg://$user@127.0.0.1:$port/$sourceDb"
    Push-Location (Join-Path $PSScriptRoot '..\..\..\backend')
    try {
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Alembic upgrade failed against the task-owned disposable database.' }
    }
    finally { Pop-Location }

    $schema = @"
CREATE TABLE backup_rehearsal_parent (
    id integer PRIMARY KEY,
    payload jsonb NOT NULL
);
CREATE TABLE backup_rehearsal_child (
    id integer PRIMARY KEY,
    parent_id integer NOT NULL REFERENCES backup_rehearsal_parent(id),
    document bytea NOT NULL
);
INSERT INTO backup_rehearsal_parent VALUES
    (1, jsonb_build_object('kind', 'synthetic', 'key', 'alpha')),
    (2, jsonb_build_object('kind', 'synthetic', 'key', 'beta'));
INSERT INTO backup_rehearsal_child VALUES
    (101, 1, decode('0001feff', 'hex')),
    (102, 2, decode('aabbccdd', 'hex'));
"@
    $null = Invoke-Query -Container $container -User $user -Database $sourceDb -Sql $schema
    $versionBefore = Invoke-Query -Container $container -User $user -Database $sourceDb -Sql "SELECT string_agg(version_num, ',' ORDER BY version_num) FROM alembic_version"
    $parentsBefore = Invoke-Query -Container $container -User $user -Database $sourceDb -Sql "SELECT count(*)::text || '|' || md5(COALESCE(string_agg(id::text || ':' || payload::text, ',' ORDER BY id), '')) FROM backup_rehearsal_parent"
    $childrenBefore = Invoke-Query -Container $container -User $user -Database $sourceDb -Sql "SELECT count(*)::text || '|' || md5(COALESCE(string_agg(id::text || ':' || parent_id::text || ':' || encode(document, 'hex'), ',' ORDER BY id), '')) FROM backup_rehearsal_child"

    $archive = "/tmp/m01-t004-$suffix.dump"
    $null = Invoke-Docker @('exec', $container, 'pg_dump', '-U', $user, '--format=custom', '--no-owner', '--no-acl', '--file', $archive, $sourceDb)
    $archiveList = Invoke-Docker @('exec', $container, 'pg_restore', '--list', $archive)
    foreach ($required in 'TABLE public backup_rehearsal_parent', 'TABLE public backup_rehearsal_child', 'TABLE public alembic_version') {
        if ($archiveList -notmatch [regex]::Escape($required)) { throw "Archive inventory is missing $required." }
    }

    $null = Invoke-Docker @('exec', $container, 'createdb', '-U', $user, '-T', 'template0', $restoreDb)
    $null = Invoke-Docker @('exec', $container, 'pg_restore', '-U', $user, '--exit-on-error', '--no-owner', '--no-acl', '--dbname', $restoreDb, $archive)
    $versionAfter = Invoke-Query -Container $container -User $user -Database $restoreDb -Sql "SELECT string_agg(version_num, ',' ORDER BY version_num) FROM alembic_version"
    $parentsAfter = Invoke-Query -Container $container -User $user -Database $restoreDb -Sql "SELECT count(*)::text || '|' || md5(COALESCE(string_agg(id::text || ':' || payload::text, ',' ORDER BY id), '')) FROM backup_rehearsal_parent"
    $childrenAfter = Invoke-Query -Container $container -User $user -Database $restoreDb -Sql "SELECT count(*)::text || '|' || md5(COALESCE(string_agg(id::text || ':' || parent_id::text || ':' || encode(document, 'hex'), ',' ORDER BY id), '')) FROM backup_rehearsal_child"
    Assert-Equal 'Alembic migration state' $versionBefore $versionAfter
    Assert-Equal 'Synthetic parent count/content' $parentsBefore $parentsAfter
    Assert-Equal 'Synthetic child count/content' $childrenBefore $childrenAfter

    Write-Output 'RESULT=PASS'
    Write-Output "POSTGRES_IMAGE=$image"
    Write-Output "POSTGRES_IMAGE_ID=$imageId"
    Write-Output "SOURCE_DB=$sourceDb"
    Write-Output "RESTORE_DB=$restoreDb"
    Write-Output "MIGRATION_STATE=$versionBefore"
    Write-Output "PARENT_COUNT_HASH=$parentsAfter"
    Write-Output "CHILD_COUNT_HASH=$childrenAfter"
    Write-Output 'ARCHIVE_INVENTORY=required application tables present'
    Write-Output 'RESTORE_TARGET=separate empty database'
    Write-Output 'NETWORK=host port bound to 127.0.0.1 only; no volume mounts'
}
finally {
    $env:DATABASE_URL = $previousDatabaseUrl
    if ($started) {
        try {
            $labelsJson = Invoke-Docker @('inspect', '--format', '{{json .Config.Labels}}', $container)
        }
        catch {
            throw "Cleanup could not verify the task-owned container $container; inspect its exact name before any cleanup. $($_.Exception.Message)"
        }
        $labels = $labelsJson | ConvertFrom-Json
        if ($labels.'codex.task' -ne 'M01.S03.T004') {
            throw "Cleanup refused: container label did not match the exact task-owned container $container."
        }
        $null = Invoke-Docker @('stop', $container)
        $remaining = Invoke-Docker @('container', 'ls', '-a', '--filter', "name=^/$container`$", '--format', '{{.Names}}')
        if ($remaining) { throw "Task-owned container remains after stop: $container." }
    }
}
