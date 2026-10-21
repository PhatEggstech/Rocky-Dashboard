$ErrorActionPreference = "Continue"
$ssh = "$env:WINDIR\System32\OpenSSH\ssh.exe"
$key = "C:\ProgramData\RockyMCPBridge\bridge_ed25519"
$log = "C:\ProgramData\RockyMCPBridge\bridge.log"

while ($true) {
    Add-Content -Path $log -Value "$(Get-Date -Format o) starting reverse database bridge"
    & $ssh -N -T `
        -i $key `
        -o BatchMode=yes `
        -o ExitOnForwardFailure=yes `
        -o ServerAliveInterval=30 `
        -o ServerAliveCountMax=3 `
        -o StrictHostKeyChecking=accept-new `
        -R 15432:127.0.0.1:5432 `
        -R 15433:10.39.93.133:5432 `
        HP@100.69.180.66 2>&1 | Add-Content -Path $log
    Add-Content -Path $log -Value "$(Get-Date -Format o) bridge exited; retrying in 10 seconds"
    Start-Sleep -Seconds 10
}
