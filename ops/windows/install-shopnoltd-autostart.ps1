# Shopnoltd WSL/k3s automatic startup and resume helper.
# Run once from an elevated PowerShell prompt on the Windows host.
#
# Normal recovery:
#   Windows boot   -> WSL -> systemd -> k3s/runner -> ArgoCD -> services
#   Windows logon  -> WSL starts again (idempotent safety net)
#   Windows resume -> WSL starts again -> systemd services recover
#
# Windows sleep suspends the WSL VM, so a sleeping PC cannot serve Shopnoltd.
# By default this helper disables AC sleep/hibernate while leaving display
# sleep unchanged. Use -AllowSleep if the host may intentionally sleep.
#
# No passwords, Kubernetes credentials, GitHub tokens, or database secrets are
# stored by this script.

[CmdletBinding()]
param(
    [string]$Distro = $env:SHOPNOLTD_WSL_DISTRO,
    [switch]$AllowSleep
)

if ([string]::IsNullOrWhiteSpace($Distro)) {
    $Distro = 'Ubuntu-24.04'
}

$TaskName = 'Shopnoltd-WSL-Autostart'
$WslPath = Join-Path $env:SystemRoot 'System32\wsl.exe'
if (-not (Test-Path $WslPath)) {
    throw "wsl.exe not found at $WslPath"
}

$Argument = "-d `"$Distro`" --exec /bin/true"
$Action = New-ScheduledTaskAction -Execute $WslPath -Argument $Argument
$Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest

# Build an event-triggered task so it also runs when Windows resumes from
# sleep/hibernate. Power-Troubleshooter Event ID 1 is emitted on resume.
$TaskXmlPath = Join-Path $env:TEMP 'Shopnoltd-WSL-Autostart.xml'
$WslCommand = [System.Security.SecurityElement]::Escape($WslPath)
$WslArguments = [System.Security.SecurityElement]::Escape($Argument)
$TaskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Start the Shopnoltd WSL distribution after Windows boot, logon, or resume so systemd can recover k3s and platform services.</Description>
    <URI>\Shopnoltd-WSL-Autostart</URI>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </BootTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription>&lt;QueryList&gt;&lt;Query Id="0" Path="System"&gt;&lt;Select Path="System"&gt;*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;</Subscription>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="System">
      <UserId>S-1-5-18</UserId>
      <LogonType>ServiceAccount</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="System">
    <Exec>
      <Command>$WslCommand</Command>
      <Arguments>$WslArguments</Arguments>
    </Exec>
  </Actions>
</Task>
"@

Set-Content -Path $TaskXmlPath -Value $TaskXml -Encoding Unicode
try {
    Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content -Raw $TaskXmlPath) -Force | Out-Null
}
finally {
    Remove-Item -Force -ErrorAction SilentlyContinue $TaskXmlPath
}

if (-not $AllowSleep) {
    # Keep the AC-powered host awake so WSL/k3s remains available. The display
    # timeout is intentionally untouched.
    powercfg /change standby-timeout-ac 0 | Out-Null
    powercfg /change hibernate-timeout-ac 0 | Out-Null
}

Write-Host "Installed $TaskName for WSL distro: $Distro"
Write-Host 'Automatic recovery triggers: Windows boot, user logon, and Windows resume.'
if ($AllowSleep) {
    Write-Host 'Sleep policy unchanged (-AllowSleep). The local server is unavailable while Windows sleeps.'
}
else {
    Write-Host 'AC sleep/hibernate disabled; display sleep remains allowed so the local server stays available.'
}
Write-Host 'WSL systemd must have k3s and the GitHub Actions runner enabled as services.'
