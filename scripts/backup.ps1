# Shopnoltd PostgreSQL backup helper
#
# The old version wrote a plaintext SQL dump and referenced obsolete Docker
# volumes. Do not use that pattern on this project.
#
# Canonical backup path:
#   .github/workflows/postgres-backup.yml
#
# Requirements for a manual run:
#   - GitHub CLI (`gh`) authenticated to this repository
#   - GitHub Actions secret BACKUP_ENCRYPTION_KEY configured
#   - the trusted self-hosted k3s runner online
#
# This helper triggers the same encrypted backup workflow used by the nightly
# schedule. No database password, plaintext dump, or encryption key is stored
# by this script.

$ErrorActionPreference = 'Stop'

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required. Install/authenticate it before running this helper."
}

$repo = 'asaduzzamanbheramara-prog/shopnoltd'
$workflow = 'postgres-backup.yml'

Write-Host "Triggering canonical encrypted PostgreSQL backup workflow..."
gh workflow run $workflow --repo $repo

if ($LASTEXITCODE -ne 0) {
    throw "Failed to dispatch $workflow."
}

Write-Host "Backup workflow dispatched successfully."
Write-Host "Monitor with: gh run list --repo $repo --workflow $workflow --limit 5"
