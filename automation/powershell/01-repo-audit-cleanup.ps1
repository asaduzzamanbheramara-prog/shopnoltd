#Requires -Version 7.0
<#
.SYNOPSIS
    Audits the shopnoltd repo for stale/duplicate files and safely archives them.

.DESCRIPTION
    Scans for known clutter patterns accumulated during the k3s recovery effort:
      - Backup files (*.bak)
      - Superseded recovery script versions (recover-*-v2.sh when a v3 exists, etc.)
      - Log/diagnostic dump folders (crashlogs, diagnostics, cluster-before-cleanup.txt)
      - Duplicate top-level folders (corrections, read-only, toolbox-fix, meet-fix)

    SAFE BY DEFAULT: this script only REPORTS candidates unless -Apply is passed.
    When -Apply is used, matched files are MOVED (not deleted) into
    <RepoRoot>\.archive\<timestamp>\ so you can restore anything if needed.

.PARAMETER RepoRoot
    Path to the shopnoltd repo root. Defaults to the WSL-mounted path used in your sessions.

.PARAMETER Apply
    Actually move matched files/folders into the archive. Without this switch,
    the script only prints what it WOULD do.

.EXAMPLE
    ./01-repo-audit-cleanup.ps1
    # Dry run - just shows what would be archived

.EXAMPLE
    ./01-repo-audit-cleanup.ps1 -Apply
    # Moves matched clutter into .archive\<timestamp>\
#>

param(
    [string]$RepoRoot = "C:\Users\asadu\PROJECTS\shopnoltd",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $RepoRoot)) {
    Write-Error "RepoRoot not found: $RepoRoot"
    exit 1
}

Set-Location $RepoRoot

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archiveDir = Join-Path $RepoRoot ".archive\$timestamp"

# --- Patterns to flag -------------------------------------------------------

$backupFiles = Get-ChildItem -Path $RepoRoot -Recurse -File -Filter "*.bak" -ErrorAction SilentlyContinue

# Recovery script version sprawl: recover-from-blank-cluster.sh, -v2.sh, -v3.sh, -v3.sh.bak
$recoveryScripts = Get-ChildItem -Path $RepoRoot -File -Filter "recover*" -ErrorAction SilentlyContinue
$recoverGroups = $recoveryScripts | Group-Object { $_.Name -replace '-v\d+(\.sh)?(\.bak)?$', '$1' -replace '\.sh$', '' }

# Extract a numeric version for correct sorting (unversioned files = version 0,
# since they predate any -vN suffix). Alphabetical sort is NOT safe here:
# "name.sh" sorts AFTER "name-v3.sh" because '.' > '-' in ASCII, which would
# incorrectly treat the unversioned base file as "newest".
function Get-ScriptVersion {
    param([string]$Name)
    if ($Name -match '-v(\d+)(\.sh)?(\.bak)?$') {
        return [int]$Matches[1]
    }
    return 0
}

$staleScripts = foreach ($group in $recoverGroups) {
    if ($group.Count -gt 1) {
        # Keep the highest version number, flag the rest as superseded.
        # .bak files always rank below their non-.bak counterpart of the same version.
        $sorted = $group.Group | Sort-Object -Property `
            @{ Expression = { Get-ScriptVersion $_.Name } }, `
            @{ Expression = { if ($_.Name -like '*.bak') { 0 } else { 1 } } }
        $sorted | Select-Object -SkipLast 1
    }
}

# Known one-off diagnostic dumps from past incident response
$diagnosticTargets = @("crashlogs", "diagnostics", "cluster-before-cleanup.txt", "build.log")
$diagnosticPaths = foreach ($name in $diagnosticTargets) {
    $p = Join-Path $RepoRoot $name
    if (Test-Path $p) { Get-Item $p }
}

# Folders that look like superseded fix attempts (named *-fix, corrections, read-only)
$fixFolders = Get-ChildItem -Path $RepoRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '(-fix$|^corrections$|^read-only$)' }

# --- Report ------------------------------------------------------------------

$allCandidates = @()
$allCandidates += $backupFiles      | ForEach-Object { [pscustomobject]@{ Category = "Backup file";       Path = $_.FullName } }
$allCandidates += $staleScripts     | ForEach-Object { [pscustomobject]@{ Category = "Superseded script"; Path = $_.FullName } }
$allCandidates += $diagnosticPaths  | ForEach-Object { [pscustomobject]@{ Category = "Diagnostic dump";   Path = $_.FullName } }
$allCandidates += $fixFolders       | ForEach-Object { [pscustomobject]@{ Category = "Fix/scratch folder";Path = $_.FullName } }

# Dedupe: a file can legitimately match more than one category (e.g. a
# recover-*.sh.bak is both a "Backup file" and a "Superseded script"). Keep
# only the first category label per unique path so nothing gets queued twice.
$allCandidates = $allCandidates | Group-Object Path | ForEach-Object { $_.Group[0] }

if ($allCandidates.Count -eq 0) {
    Write-Host "No clutter candidates found. Repo looks clean." -ForegroundColor Green
    exit 0
}

Write-Host "`nFound $($allCandidates.Count) cleanup candidates:`n" -ForegroundColor Cyan
$allCandidates | Format-Table Category, Path -AutoSize

if (-not $Apply) {
    Write-Host "`nDRY RUN — nothing was moved. Re-run with -Apply to archive these." -ForegroundColor Yellow
    exit 0
}

# --- Apply: move to archive, preserving relative paths ----------------------

New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null

$failed = 0
foreach ($item in $allCandidates) {
    $relative = $item.Path.Substring($RepoRoot.Length).TrimStart('\', '/')
    $dest = Join-Path $archiveDir $relative
    $destParent = Split-Path $dest -Parent
    try {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
        Move-Item -Path $item.Path -Destination $dest -Force -ErrorAction Stop
        Write-Host "Archived: $relative" -ForegroundColor DarkGray
    } catch {
        Write-Host "FAILED to archive $relative : $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

$succeeded = $allCandidates.Count - $failed
Write-Host "`nDone. $succeeded of $($allCandidates.Count) items moved to:" -ForegroundColor Green
Write-Host "  $archiveDir" -ForegroundColor Green
if ($failed -gt 0) {
    Write-Host "$failed item(s) failed to move — see FAILED lines above." -ForegroundColor Red
}
Write-Host "`nReview the archive, and once confident, delete it manually or via:" -ForegroundColor Cyan
Write-Host "  Remove-Item '$archiveDir' -Recurse -Force" -ForegroundColor Cyan
