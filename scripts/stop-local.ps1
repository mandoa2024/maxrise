$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root ".local"
$PidFile = Join-Path $Runtime "processes.json"

if (Test-Path $PidFile) {
    $Processes = Get-Content $PidFile -Raw | ConvertFrom-Json
    foreach ($Id in @($Processes.server, $Processes.analyzer, $Processes.agent, $Processes.web)) {
        if ($Id) { Stop-Process -Id $Id -Force }
    }
    Remove-Item $PidFile -Force
}

Write-Output "Mini-Drop application processes stopped"
