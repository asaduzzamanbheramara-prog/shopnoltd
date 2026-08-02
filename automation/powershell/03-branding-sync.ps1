#Requires -Version 7.0
<#
.SYNOPSIS
    Syncs Shopnoltd branding assets (logo, favicon, app name) out to each portal.

.DESCRIPTION
    Reads a branding manifest (branding-manifest.json) describing which files
    from the repo's /branding folder map to which destination path in each
    portal/app. Copies them over and reports what changed. Safe to re-run;
    only overwrites files that actually differ (by hash).

    You maintain branding-manifest.json — this script does not guess file
    locations, since every portal (React web-portal, Android app under
    /mobile, Keycloak theme, etc.) has a different asset layout.

.PARAMETER RepoRoot
    Path to the shopnoltd repo root.

.PARAMETER ManifestPath
    Path to the branding manifest JSON. Defaults to <RepoRoot>\branding\branding-manifest.json.

.PARAMETER WhatIf
    Standard PowerShell WhatIf support — preview changes without copying.

.EXAMPLE
    ./03-branding-sync.ps1

.EXAMPLE
    ./03-branding-sync.ps1 -WhatIf
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$RepoRoot = "C:\Users\asadu\PROJECTS\shopnoltd",
    [string]$ManifestPath = ""
)

$ErrorActionPreference = "Stop"

if (-not $ManifestPath) {
    $ManifestPath = Join-Path $RepoRoot "branding\branding-manifest.json"
}

if (-not (Test-Path $ManifestPath)) {
    Write-Host "No manifest found at $ManifestPath — creating a starter template." -ForegroundColor Yellow

    $template = @{
        assets = @(
            @{
                source      = "branding\logo.svg"
                description = "Primary logo (SVG)"
                targets     = @(
                    "frontend\web-portal\public\logo.svg",
                    "frontend\admin-portal\public\logo.svg"
                )
            },
            @{
                source      = "branding\favicon.ico"
                description = "Favicon"
                targets     = @(
                    "frontend\web-portal\public\favicon.ico",
                    "frontend\admin-portal\public\favicon.ico"
                )
            },
            @{
                source      = "branding\app-icon-android.png"
                description = "Android app launcher icon"
                targets     = @(
                    "mobile\android-portal\app\src\main\res\mipmap-xxxhdpi\ic_launcher.png"
                )
            },
            @{
                source      = "branding\keycloak-logo.png"
                description = "Keycloak login theme logo"
                targets     = @(
                    "docker\keycloak\themes\shopnoltd\login\resources\img\logo.png"
                )
            }
        )
        app_name = "Shopnoltd"
    }

    $templateDir = Split-Path $ManifestPath -Parent
    New-Item -ItemType Directory -Path $templateDir -Force | Out-Null
    $template | ConvertTo-Json -Depth 6 | Set-Content -Path $ManifestPath -Encoding UTF8

    Write-Host "Template written to $ManifestPath — edit source/target paths to match your actual repo layout, then re-run." -ForegroundColor Yellow
    exit 0
}

$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json

function Get-FileHashSafe {
    param([string]$Path)
    if (Test-Path $Path) {
        return (Get-FileHash -Path $Path -Algorithm SHA256).Hash
    }
    return $null
}

$copied = 0
$skipped = 0
$missing = 0

foreach ($asset in $manifest.assets) {
    $sourcePath = Join-Path $RepoRoot $asset.source

    if (-not (Test-Path $sourcePath)) {
        Write-Host "MISSING SOURCE: $($asset.source) ($($asset.description))" -ForegroundColor Red
        $missing++
        continue
    }

    $sourceHash = Get-FileHashSafe -Path $sourcePath

    foreach ($target in $asset.targets) {
        $destPath = Join-Path $RepoRoot $target
        $destHash = Get-FileHashSafe -Path $destPath

        if ($sourceHash -eq $destHash) {
            Write-Verbose "Unchanged: $target"
            $skipped++
            continue
        }

        if ($PSCmdlet.ShouldProcess($destPath, "Copy branding asset from $($asset.source)")) {
            $destParent = Split-Path $destPath -Parent
            New-Item -ItemType Directory -Path $destParent -Force | Out-Null
            Copy-Item -Path $sourcePath -Destination $destPath -Force
            Write-Host "Updated: $target" -ForegroundColor Green
            $copied++
        }
    }
}

Write-Host "`nBranding sync summary:" -ForegroundColor Cyan
Write-Host "  Updated: $copied" -ForegroundColor Green
Write-Host "  Unchanged: $skipped" -ForegroundColor DarkGray
Write-Host "  Missing sources: $missing" -ForegroundColor $(if ($missing -gt 0) { "Red" } else { "DarkGray" })

if ($manifest.app_name) {
    Write-Host "`nNote: app display name ('$($manifest.app_name)') in package.json / strings.xml / AndroidManifest.xml" -ForegroundColor Yellow
    Write-Host "is NOT auto-replaced by this script — those need per-project text edits since context varies." -ForegroundColor Yellow
}
