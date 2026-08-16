param(
    [Parameter(Mandatory = $true)][string]$ReleaseDirectory,
    [Parameter(Mandatory = $true)][string]$PythonExe
)

$ErrorActionPreference = "Stop"
$root = "C:\ProgramData\RockyMCP"
$serviceDir = Join-Path $root "service"
$current = Join-Path $root "current"

foreach ($path in @($root, $serviceDir, (Join-Path $root "config"), (Join-Path $root "logs"))) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}

$venv = Join-Path $ReleaseDirectory "venv"
if (-not (Test-Path $venv)) {
    & $PythonExe -m venv $venv
}
& (Join-Path $venv "Scripts\python.exe") -m pip install --upgrade pip
& (Join-Path $venv "Scripts\python.exe") -m pip install -r (Join-Path $ReleaseDirectory "deploy\rocky_mcp_windows\requirements.txt")

if (-not (Test-Path (Join-Path $serviceDir "RockyMCP.exe"))) {
    $url = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
    Invoke-WebRequest -Uri $url -OutFile (Join-Path $serviceDir "RockyMCP.exe")
}
Copy-Item (Join-Path $ReleaseDirectory "deploy\rocky_mcp_windows\RockyMCP.xml") (Join-Path $serviceDir "RockyMCP.xml") -Force

if (Test-Path $current) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Rename-Item -Path $current -NewName "current.previous.$stamp"
}
New-Item -ItemType Junction -Path $current -Target $ReleaseDirectory | Out-Null

$serviceExe = Join-Path $serviceDir "RockyMCP.exe"
$serviceExists = Get-Service RockyMCP -ErrorAction SilentlyContinue
if (-not $serviceExists) {
    & $serviceExe install (Join-Path $serviceDir "RockyMCP.xml")
} else {
    Stop-Service RockyMCP -ErrorAction SilentlyContinue
    & $serviceExe refresh (Join-Path $serviceDir "RockyMCP.xml")
}
Start-Service RockyMCP
Get-Service RockyMCP | Format-Table Name, Status, StartType -AutoSize
