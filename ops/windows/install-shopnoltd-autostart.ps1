# Shopnoltd WSL/k3s automatic startup helper.
# Run once from an elevated PowerShell prompt on the Windows host.
# The task starts the WSL distribution after Windows boot. WSL systemd then
# starts enabled services such as k3s and the GitHub Actions runner service.

[CmdletBinding()]
param(
    [string]$Distro = $env:SHOPNOLTD_WSL_DISTRO
)

if ([string]::IsNullOrWhiteSpace($Distro)) {
    $Distro = 'Ubuntu-24.04'
}

$TaskName = 'Shopnoltd-WSL-Autostart'
$WslPath = Join-Path $env:SystemRoot 'System32\wsl.exe'
if (-not (Test-Path $WslPath)) {
    throw "wsl.exe not found at $WslPath"
}

# Starting the distro is sufficient when WSL systemd is enabled. Do not put
# passwords, Kubernetes credentials, GitHub tokens, or database secrets here.
$Action = New-ScheduledTaskAction -Execute $WslPath -Argument "-d `"$Distro`" --exec /bin/true"
$Trigger = New-ScheduledTaskTrigger -AtStartup -RandomDelay (New-TimeSpan -Seconds 30)
$Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null

Write-Host "Installed $TaskName for WSL distro: $Distro"
Write-Host 'After Windows reboot: WSL starts -> systemd -> k3s -> ArgoCD -> services.'
Write-Host 'The GitHub runner must already be installed as a system service inside WSL.'
