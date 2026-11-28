param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_-]{10,100}$')]
    [string]$DeviceId,
    [string]$GatewayUrl = 'https://devices.shopnoltd.dpdns.org'
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if ($GatewayUrl -notmatch '^https://') { throw 'The Shopnoltd gateway must use HTTPS.' }

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Open PowerShell with Run as administrator, then run this installer again.'
}

$python = Get-Command python.exe -ErrorAction SilentlyContinue
$pythonArgs = ''
if (-not $python) {
    $python = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($python) { $pythonArgs = '-3' }
}
if (-not $python) {
    throw 'Python 3 is required. Install Python 3.12, reopen PowerShell, and retry.'
}
if ($pythonArgs) {
    $versionOutput = & $python.Source $pythonArgs --version 2>&1
} else {
    $versionOutput = & $python.Source --version 2>&1
}
if ($LASTEXITCODE -ne 0) { throw 'Python 3 could not be started.' }

$root = Join-Path $env:ProgramData 'Shopnoltd'
New-Item -ItemType Directory -Path $root -Force | Out-Null
& icacls.exe $root /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the Shopnoltd agent directory permissions.' }

$agentPath = Join-Path $root 'agent.py'
$configPath = Join-Path $root 'executor.json'
$agentUrl = 'https://raw.githubusercontent.com/asaduzzamanbheramara-prog/shopnoltd/main/platform/remote-device/executor/agent.py'
$expectedAgentHash = 'd6716448b7fe65d33b1658a24c6ba1dd18a262a2e5f75d53e9db48cea01ba32d'
Invoke-WebRequest -UseBasicParsing -Uri $agentUrl -OutFile $agentPath
$actualAgentHash = (Get-FileHash -Path $agentPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualAgentHash -ne $expectedAgentHash) {
    Remove-Item -Path $agentPath -Force -ErrorAction SilentlyContinue
    throw 'Downloaded Shopnoltd agent failed its SHA-256 integrity check.'
}

$pairingSecret = Read-Host 'Paste the one-time Shopnoltd pairing code (input hidden)' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pairingSecret)
try {
    $pairingCode = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    if ([string]::IsNullOrWhiteSpace($pairingCode) -or $pairingCode.Length -lt 20) {
        throw 'The pairing code is missing or invalid.'
    }
    $pairingBody = @{
        pairing_secret = $pairingCode
        hostname = $env:COMPUTERNAME
        platform = 'windows'
        agent_version = '2.1'
    } | ConvertTo-Json -Compress
    $pairing = Invoke-RestMethod -Uri ($GatewayUrl.TrimEnd('/') + '/api/pairing/consume') -Method Post -ContentType 'application/json' -Body $pairingBody
    if (-not $pairing.enrollment_token) { throw 'Pairing service did not return an enrollment grant.' }
    $config = [ordered]@{
        gateway_url = $GatewayUrl.TrimEnd('/')
        device_id = $DeviceId
        enrollment_token = $pairing.enrollment_token
    }
    $json = $config | ConvertTo-Json -Depth 4
    [IO.File]::WriteAllText($configPath, $json, [Text.UTF8Encoding]::new($false))
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    $pairingCode = $null
    $pairingSecret.Dispose()
}
& icacls.exe $configPath /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the Shopnoltd credential file permissions.' }

$account = $identity.Name
$taskArgs = if ($pythonArgs) { $pythonArgs + ' "' + $agentPath + '"' } else { '"' + $agentPath + '"' }
$action = New-ScheduledTaskAction -Execute $python.Source -Argument $taskArgs
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $account
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName 'Shopnoltd Device Agent' -Action $action -Trigger $trigger -Principal $taskPrincipal -Description 'Outbound-only Shopnoltd device heartbeat and approved diagnostics.' -Force | Out-Null
Start-ScheduledTask -TaskName 'Shopnoltd Device Agent'

Write-Host 'Shopnoltd device agent installed and started.' -ForegroundColor Green
Write-Host 'The agent uses outbound HTTPS only and runs a fixed allowlist of diagnostics.'
Write-Host 'Refresh Shopnoltd My Devices after 30-90 seconds to confirm the heartbeat.'
Write-Host 'This agent does not enable remote screen control; desktop screen access needs the separately authorized MeshCentral agent.'
