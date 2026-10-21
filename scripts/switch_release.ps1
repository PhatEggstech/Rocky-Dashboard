param(
    [Parameter(Mandatory = $true)][string]$ServiceName,
    [Parameter(Mandatory = $true)][string]$LinkPath,
    [Parameter(Mandatory = $true)][string]$ReleasePath,
    [Parameter(Mandatory = $true)][string]$RollbackLinkPath
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ReleasePath -PathType Container)) {
    throw "Release does not exist: $ReleasePath"
}

$link = Get-Item -LiteralPath $LinkPath -Force
if ($link.LinkType -ne 'Junction') {
    throw "Refusing to replace a non-junction path: $LinkPath"
}

$oldTarget = (fsutil reparsepoint query $LinkPath | Select-String 'Substitute Name:' |
    ForEach-Object { $_.Line -replace '^.*Substitute Name:\s+\\\?\?\\', '' }).Trim()
if (-not $oldTarget -or -not (Test-Path -LiteralPath $oldTarget -PathType Container)) {
    throw "Could not resolve the current release target for $LinkPath"
}

if (Test-Path -LiteralPath $RollbackLinkPath) {
    $existingRollback = Get-Item -LiteralPath $RollbackLinkPath -Force
    if ($existingRollback.LinkType -ne 'Junction') {
        throw "Refusing to replace a non-junction rollback path: $RollbackLinkPath"
    }
    cmd /c "rmdir $RollbackLinkPath"
}
cmd /c mklink /J $RollbackLinkPath $oldTarget | Out-Null

Stop-Service -Name $ServiceName -Force
cmd /c "rmdir $LinkPath"
cmd /c mklink /J $LinkPath $ReleasePath | Out-Null
Start-Service -Name $ServiceName

(Get-Service -Name $ServiceName) | Select-Object Name, Status
Write-Output "RollbackLink=$RollbackLinkPath"
Write-Output "RollbackTarget=$oldTarget"
