$ErrorActionPreference = "Continue"

$service = Get-Service RockyMCP -ErrorAction SilentlyContinue
$health = $null
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8085/health" -TimeoutSec 10
} catch {
    $health = $_.Exception.Message
}

[pscustomobject]@{
    ServiceStatus = if ($service) { $service.Status } else { "Missing" }
    ServiceStartType = if ($service) { $service.StartType } else { "Missing" }
    DashboardBridge = (Test-NetConnection 127.0.0.1 -Port 15432 -InformationLevel Quiet)
    PosBridge = (Test-NetConnection 127.0.0.1 -Port 15433 -InformationLevel Quiet)
    Health = ($health | ConvertTo-Json -Compress)
}
