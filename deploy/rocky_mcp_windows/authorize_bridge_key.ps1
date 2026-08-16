param(
    [Parameter(Mandatory = $true)][string]$PublicKeyFile
)

$ErrorActionPreference = "Stop"
$authFile = "C:\ProgramData\ssh\administrators_authorized_keys"
$publicKey = (Get-Content $PublicKeyFile -Raw).Trim()
if (-not (Test-Path $authFile)) {
    New-Item -ItemType File -Path $authFile -Force | Out-Null
}
$existing = Get-Content $authFile -Raw
if (-not $existing.Contains($publicKey)) {
    Add-Content -Path $authFile -Value $publicKey -Encoding ascii
}
& icacls.exe $authFile /inheritance:r /grant:r "SYSTEM:F" "BUILTIN\Administrators:F" | Out-Null
Restart-Service sshd
Write-Output "Bridge public key authorized."
