param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("staging", "production")]
    [string]$Target,

    [string]$SourceDirectory = (Resolve-Path (Join-Path $PSScriptRoot "..\..")),
    [string]$ReleaseId = (Get-Date -Format "yyyyMMdd_HHmmss"),
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$root = "C:\ProgramData\RockyMCP"
$releases = Join-Path $root "releases"
$release = Join-Path $releases $ReleaseId
$envFile = if ($Target -eq "staging") {
    Join-Path $root "config\.env.staging"
} else {
    Join-Path $root "config\.env"
}

if (-not (Test-Path $envFile)) {
    throw "Missing runtime configuration: $envFile"
}
if (Test-Path $release) {
    throw "Release already exists: $release"
}

New-Item -ItemType Directory -Path $releases -Force | Out-Null
New-Item -ItemType Directory -Path $release -Force | Out-Null

# Copy source only. Runtime configuration, auth databases, logs, and previous
# virtual environments stay outside the release directory.
$robocopyArgs = @(
    $SourceDirectory, $release, "/MIR",
    "/XD", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "logs", "outputs",
    "/XF", ".env", ".env.*", "*.sqlite3", "*.sqlite3-*", "*.pyc"
)
& robocopy @robocopyArgs | Out-Host
if ($LASTEXITCODE -gt 7) {
    throw "robocopy failed with exit code $LASTEXITCODE"
}

& $PythonExe -m venv (Join-Path $release "venv")
$releasePython = Join-Path $release "venv\Scripts\python.exe"
& $releasePython -m pip install --upgrade pip
& $releasePython -m pip install -r (Join-Path $release "requirements.txt")
Push-Location $release
try {
    & $releasePython -m compileall -q mcp_server scripts
    & $releasePython -m pytest tests -q
    if ($LASTEXITCODE -ne 0) {
        throw "Release tests failed."
    }
} finally {
    Pop-Location
}

if ($Target -eq "staging") {
    & (Join-Path $release "deploy\rocky_mcp_windows\install_staging.ps1") -ReleaseDirectory $release
    $healthUrl = "http://127.0.0.1:8086/health"
} else {
    & (Join-Path $release "deploy\rocky_mcp_windows\install_release.ps1") `
        -ReleaseDirectory $release -PythonExe $PythonExe
    $healthUrl = "http://127.0.0.1:8085/health"
}

$health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 10
if ($health.status -ne "ok") {
    throw "Unexpected health response: $($health | ConvertTo-Json -Compress)"
}

[pscustomobject]@{
    Target = $Target
    Release = $release
    Health = $health.status
} | Format-List
