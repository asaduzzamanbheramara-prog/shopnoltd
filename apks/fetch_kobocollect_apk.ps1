<#
.SYNOPSIS
Downloads the latest KoBoCollect APK from GitHub releases (kobotoolbox/collect).

.DESCRIPTION
This script queries the GitHub Releases API for the `kobotoolbox/collect` repository,
finds the latest APK asset and downloads it to the current directory (or `-OutDir`).

.PARAMETER Tag
Optional release tag to download (defaults to latest).

.PARAMETER OutDir
Output directory for the downloaded APK. Defaults to the script directory.

.EXAMPLE
PS> .\fetch_kobocollect_apk.ps1
PS> .\fetch_kobocollect_apk.ps1 -OutDir .\apks
PS> .\fetch_kobocollect_apk.ps1 -Tag v4.21.3
#>

[CmdletBinding()]
param(
    [string]$Tag,
    [string]$OutDir = "$PSScriptRoot"
)

function Write-ErrorAndExit {
    param($Message)
    Write-Error $Message
    exit 1
}

if (-not (Test-Path -Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$headers = @{ 'User-Agent' = 'fetch-kobocollect-apk-script' }

try {
    if ($Tag) {
        $apiUrl = "https://api.github.com/repos/kobotoolbox/collect/releases/tags/$Tag"
    } else {
        $apiUrl = 'https://api.github.com/repos/kobotoolbox/collect/releases/latest'
    }

    $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers -ErrorAction Stop
} catch {
    Write-ErrorAndExit "Failed to query GitHub Releases API: $($_.Exception.Message)"
}

if (-not $release.assets -or $release.assets.Count -eq 0) {
    Write-ErrorAndExit "No assets found for release '$($release.tag_name)'."
}

# Prefer assets that end with .apk
$apkAsset = $release.assets | Where-Object { $_.name -match '\.apk$' } | Select-Object -First 1

if (-not $apkAsset) {
    Write-ErrorAndExit "No APK asset found in release '$($release.tag_name)'."
}

$outFileName = "$($apkAsset.name)"
$outPath = Join-Path -Path $OutDir -ChildPath $outFileName

Write-Host "Downloading APK '$($apkAsset.name)' from release '$($release.tag_name)'..."

try {
    Invoke-WebRequest -Uri $apkAsset.browser_download_url -Headers $headers -OutFile $outPath -UseBasicParsing -ErrorAction Stop
} catch {
    Write-ErrorAndExit "Failed to download APK: $($_.Exception.Message)"
}

Write-Host "Saved: $outPath"
