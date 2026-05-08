param(
    [string]$DumpPath = ".\\mstechnics.dump",
    [string]$ComposeProjectDir = "."
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path $ComposeProjectDir).Path
$dumpFullPath = (Resolve-Path $DumpPath).Path
$compatSqlPath = Join-Path $repoRoot "scripts\\prod_dump_compat.sql"
$envFilePath = Join-Path $repoRoot "Config\\.env"

Set-Location $repoRoot

if (-not (Test-Path $envFilePath)) {
    throw "Config/.env not found"
}

$envMap = @{}
Get-Content $envFilePath | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') {
        return
    }
    $parts = $_ -split '=', 2
    if ($parts.Count -eq 2) {
        $envMap[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$pgUser = $envMap["POSTGRES_USER"]
$pgPassword = $envMap["POSTGRES_PASSWORD"]
$pgDb = $envMap["POSTGRES_DB"]

if (-not $pgUser -or -not $pgPassword -or -not $pgDb) {
    throw "POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB must be set in Config/.env"
}

docker compose down -v --remove-orphans

docker compose up -d db

$dbContainer = (docker compose ps -q db).Trim()
if (-not $dbContainer) {
    throw "db container not found"
}

docker cp $dumpFullPath "${dbContainer}:/tmp/mstechnics.dump"
docker exec $dbContainer sh -lc "PGPASSWORD=`"$pgPassword`" pg_restore --clean --if-exists --no-owner --no-privileges -U `"$pgUser`" -d `"$pgDb`" /tmp/mstechnics.dump"
Get-Content -Raw $compatSqlPath | docker exec -i $dbContainer psql -U $pgUser -d $pgDb

docker compose up -d --build redis web
