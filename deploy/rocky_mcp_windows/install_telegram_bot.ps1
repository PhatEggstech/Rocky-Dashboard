param(
    [string]$Root = "C:\ProgramData\RockyMCP"
)

$ErrorActionPreference = "Stop"
$serviceDir = Join-Path $Root "service"
$current = Join-Path $Root "current"
$envFile = Join-Path $Root "config\.env"
$serviceExe = Join-Path $serviceDir "RockyTelegramBot.exe"

if (-not (Test-Path (Join-Path $current "scripts\run_telegram_bot.py"))) {
    throw "Current Rocky MCP release does not include the Telegram adapter. Promote a tested release first."
}
if (-not (Test-Path $envFile)) {
    throw "Missing $envFile. Configure Telegram settings on the customer host first."
}

$envText = Get-Content -Raw $envFile
if ($envText -notmatch '(?m)^TELEGRAM_BOT_TOKEN=.+') {
    throw "TELEGRAM_BOT_TOKEN is not configured in $envFile."
}
if ($envText -notmatch '(?m)^TELEGRAM_ALLOWED_CHAT_IDS=.+') {
    throw "TELEGRAM_ALLOWED_CHAT_IDS is not configured in $envFile."
}

New-Item -ItemType Directory -Path $serviceDir -Force | Out-Null
if (-not (Test-Path $serviceExe)) {
    Invoke-WebRequest `
        -Uri "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe" `
        -OutFile $serviceExe
}

Copy-Item (Join-Path $current "deploy\rocky_mcp_windows\RockyTelegramBot.xml") `
    (Join-Path $serviceDir "RockyTelegramBot.xml") -Force

$existing = Get-Service RockyTelegramBot -ErrorAction SilentlyContinue
if ($existing) {
    Stop-Service RockyTelegramBot -ErrorAction SilentlyContinue
} else {
    & $serviceExe install (Join-Path $serviceDir "RockyTelegramBot.xml")
}
Start-Service RockyTelegramBot
Start-Sleep -Seconds 3
$service = Get-Service RockyTelegramBot
if ($service.Status -ne 'Running') {
    throw "RockyTelegramBot did not start. Check $Root\logs\telegram_bot.log."
}

$service | Format-Table Name, Status, StartType -AutoSize
