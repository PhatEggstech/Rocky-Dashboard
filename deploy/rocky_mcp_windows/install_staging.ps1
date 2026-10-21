param(
    [Parameter(Mandatory = $true)][string]$ReleaseDirectory
)

$ErrorActionPreference = "Stop"
$root = "C:\ProgramData\RockyMCP"
$serviceDir = Join-Path $root "service"
$staging = Join-Path $root "staging"
$logs = Join-Path $root "logs\staging"

foreach ($path in @($root, $serviceDir, $logs)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}

$python = Join-Path $ReleaseDirectory "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Staging release does not contain a Python environment: $python"
}

if (Test-Path $staging) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Rename-Item -Path $staging -NewName "staging.previous.$stamp"
}
New-Item -ItemType Junction -Path $staging -Target $ReleaseDirectory | Out-Null

$serviceExe = Join-Path $serviceDir "RockyMCPStaging.exe"
$serviceXml = Join-Path $serviceDir "RockyMCPStaging.xml"
if (-not (Test-Path $serviceExe)) {
    Copy-Item (Join-Path $serviceDir "RockyMCP.exe") $serviceExe
}
Copy-Item (Join-Path $ReleaseDirectory "deploy\rocky_mcp_windows\RockyMCPStaging.xml") $serviceXml -Force

$existing = Get-Service RockyMCPStaging -ErrorAction SilentlyContinue
if (-not $existing) {
    & $serviceExe install $serviceXml
} else {
    Stop-Service RockyMCPStaging -ErrorAction SilentlyContinue
    & $serviceExe refresh $serviceXml
}

Start-Service RockyMCPStaging
Get-Service RockyMCPStaging | Select-Object Name, Status, StartType
