$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root ".local"
$PostgresBin = "C:\Program Files\PostgreSQL\18\bin"
$PostgresData = Join-Path $Runtime "postgres-data"
$PostgresLog = Join-Path $Runtime "postgres.log"
$PidFile = Join-Path $Runtime "processes.json"

New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

if (-not (Test-Path (Join-Path $PostgresData "PG_VERSION"))) {
    & (Join-Path $PostgresBin "initdb.exe") -D $PostgresData -U drop -A trust --encoding=UTF8 --locale=C
}

& (Join-Path $PostgresBin "pg_isready.exe") -h 127.0.0.1 -p 55432 *> $null
if ($LASTEXITCODE -ne 0) {
    & (Join-Path $PostgresBin "pg_ctl.exe") -D $PostgresData -l $PostgresLog -o "-p 55432" start
}

& (Join-Path $PostgresBin "psql.exe") -h 127.0.0.1 -p 55432 -U drop -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='drop'" | Out-Null
$DatabaseExists = & (Join-Path $PostgresBin "psql.exe") -h 127.0.0.1 -p 55432 -U drop -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='drop'"
if ($DatabaseExists.Trim() -ne "1") {
    & (Join-Path $PostgresBin "createdb.exe") -h 127.0.0.1 -p 55432 -U drop drop
}
& (Join-Path $PostgresBin "psql.exe") -h 127.0.0.1 -p 55432 -U drop -d drop -f (Join-Path $Root "migrations\001_init.sql") | Out-Null

if (Test-Path $PidFile) {
    & (Join-Path $PSScriptRoot "stop-local.ps1")
}

function Start-HiddenProcess([string[]]$Arguments) {
    $Info = [System.Diagnostics.ProcessStartInfo]::new()
    $Info.FileName = "python"
    $Info.WorkingDirectory = $Root
    $Info.UseShellExecute = $true
    $Info.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $Info.Arguments = ($Arguments -join " ")
    return [System.Diagnostics.Process]::Start($Info)
}

$env:DATABASE_URL = "postgresql://drop@127.0.0.1:55432/drop"
$env:ANALYZER_URL = "http://127.0.0.1:8090"
$Server = Start-HiddenProcess @("-m", "uvicorn", "server.app.main:app", "--host", "127.0.0.1", "--port", "8080")

$Analyzer = Start-HiddenProcess @("-m", "uvicorn", "analyzer.main:app", "--host", "127.0.0.1", "--port", "8090")

$env:SERVER_URL = "http://127.0.0.1:8080"
$env:AGENT_ID = "demo-agent"
$env:AGENT_NAME = "demo-agent"
$env:DEMO_MODE = "true"
$Agent = Start-HiddenProcess @("-m", "agent.main")

$Web = Start-HiddenProcess @("-m", "http.server", "3000", "--bind", "127.0.0.1", "--directory", "web")

@{
    server = $Server.Id
    analyzer = $Analyzer.Id
    agent = $Agent.Id
    web = $Web.Id
} | ConvertTo-Json | Set-Content -Encoding UTF8 $PidFile

$Deadline = (Get-Date).AddSeconds(30)
do {
    try {
        Invoke-RestMethod http://127.0.0.1:8080/healthz | Out-Null
        Invoke-RestMethod http://127.0.0.1:8090/healthz | Out-Null
        Invoke-WebRequest http://127.0.0.1:3000 -UseBasicParsing | Out-Null
        Write-Output "Mini-Drop is running at http://localhost:3000"
        exit 0
    } catch {
        Start-Sleep -Seconds 1
    }
} while ((Get-Date) -lt $Deadline)

Write-Error "Mini-Drop did not become healthy. Check whether ports 3000, 8080 and 8090 are available."
