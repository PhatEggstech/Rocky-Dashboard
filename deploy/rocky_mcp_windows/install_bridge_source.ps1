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
& icacls.exe $key /inheritance:r /grant:r "*S-1-5-18:F" | Out-Null
& icacls.exe $key /setowner "*S-1-5-18" | Out-Null
& icacls.exe $key /remove:g "BUILTIN\Administrators" "$env:COMPUTERNAME\$env:USERNAME" | Out-Null
$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""
& schtasks.exe /Create /TN "RockyCustomerDBBridge" /TR $taskCommand /SC ONSTART /RU SYSTEM /RL HIGHEST /F | Out-Null
$task = Get-ScheduledTask -TaskName "RockyCustomerDBBridge"
$task.Settings.ExecutionTimeLimit = "PT0S"
$task.Settings.DisallowStartIfOnBatteries = $false
$task.Settings.StopIfGoingOnBatteries = $false
Set-ScheduledTask -InputObject $task | Out-Null
Get-Content "$key.pub"
