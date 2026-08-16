param(
    [Parameter(Mandatory = $true)][string]$ReleaseDirectory,
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [int]$HealthPort = 8085,
    [int]$HealthTimeoutSeconds = 45
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

$serviceExe = Join-Path $serviceDir "RockyMCP.exe"
$serviceExists = Get-Service RockyMCP -ErrorAction SilentlyContinue
$previousTarget = $null
if (Test-Path $current) {
    $previousTarget = (Get-Item $current).Target
}

function Wait-ForHealth {
    $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
    do {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$HealthPort/health" -TimeoutSec 5
            if ($health.status -eq "ok") {
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)

    throw "RockyMCP did not pass the health check on port $HealthPort within $HealthTimeoutSeconds seconds."
}

try {
    if ($serviceExists) {
        Stop-Service RockyMCP -ErrorAction SilentlyContinue
    }

    if (Test-Path $current) {
        Remove-Item -LiteralPath $current -Force
    }
    New-Item -ItemType Junction -Path $current -Target $ReleaseDirectory | Out-Null

    if (-not $serviceExists) {
        & $serviceExe install (Join-Path $serviceDir "RockyMCP.xml")
    }

    Start-Service RockyMCP
    Wait-ForHealth
} catch {
    $deployError = $_
    Write-Warning "Production deployment failed. Restoring the previous release."
    Stop-Service RockyMCP -ErrorAction SilentlyContinue
    if (Test-Path $current) {
        Remove-Item -LiteralPath $current -Force
    }
    if ($previousTarget) {
        New-Item -ItemType Junction -Path $current -Target $previousTarget | Out-Null
        Start-Service RockyMCP -ErrorAction SilentlyContinue
    }
    throw $deployError
}

Get-Service RockyMCP | Format-Table Name, Status, StartType -AutoSize
