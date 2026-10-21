param(
    [Parameter(Mandatory = $true)][string]$SourceScript
)

$ErrorActionPreference = "Stop"
$bridgeDir = "C:\ProgramData\RockyMCPBridge"
$key = Join-Path $bridgeDir "bridge_ed25519"
$script = Join-Path $bridgeDir "rocky_db_bridge.ps1"

New-Item -ItemType Directory -Path $bridgeDir -Force | Out-Null
Copy-Item $SourceScript $script -Force
if (-not (Test-Path $key)) {
    & "$env:WINDIR\System32\OpenSSH\ssh-keygen.exe" -q -t ed25519 -f $key -N '""' -C "rocky-mcp-db-bridge"
}

& icacls.exe $bridgeDir /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" | Out-Null
$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""
& schtasks.exe /Create /TN "RockyCustomerDBBridge" /TR $taskCommand /SC ONSTART /RU SYSTEM /RL HIGHEST /F | Out-Null
Get-Content "$key.pub"
