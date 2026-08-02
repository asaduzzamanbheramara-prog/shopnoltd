#Requires -Version 7.0
<#
.SYNOPSIS
    Rotates OAuth provider secrets into a Kubernetes Secret (never hardcoded).

.DESCRIPTION
    Reads new OAuth client ID/secret values from parameters (or, if omitted,
    prompts securely) and writes them into a Kubernetes Secret named
    'oauth-provider-credentials' in the shopno-identity namespace. Services
    (auth-service, oauth-service, keycloak) should reference this Secret via
    envFrom / secretKeyRef rather than having values inlined in a Deployment
    manifest.

    IMPORTANT: Rotate the actual credentials in the Google/Facebook/GitHub
    developer consoles FIRST. This script only updates the cluster's copy —
    it does not talk to those providers.

.PARAMETER Namespace
    Target namespace. Defaults to shopno-identity.

.EXAMPLE
    ./02-k8s-oauth-secrets-rotate.ps1
    # Prompts securely for each value, then applies

.EXAMPLE
    ./02-k8s-oauth-secrets-rotate.ps1 -GoogleClientId "xxx" -GoogleClientSecret (Read-Host -AsSecureString)
#>

param(
    [string]$Namespace = "shopno-identity",

    [string]$GoogleClientId,
    [SecureString]$GoogleClientSecret,

    [string]$FacebookAppId,
    [SecureString]$FacebookAppSecret,

    [string]$GitHubClientId,
    [SecureString]$GitHubClientSecret
)

$ErrorActionPreference = "Stop"

function Get-SecretPlainText {
    param([SecureString]$Secure, [string]$PromptLabel)
    if (-not $Secure) {
        $Secure = Read-Host -Prompt $PromptLabel -AsSecureString
    }
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    } finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

if (-not $GoogleClientId)  { $GoogleClientId  = Read-Host "Google Client ID" }
if (-not $FacebookAppId)   { $FacebookAppId   = Read-Host "Facebook App ID" }
if (-not $GitHubClientId)  { $GitHubClientId  = Read-Host "GitHub Client ID" }

$googleSecretPlain   = Get-SecretPlainText -Secure $GoogleClientSecret   -PromptLabel "Google Client Secret"
$facebookSecretPlain = Get-SecretPlainText -Secure $FacebookAppSecret    -PromptLabel "Facebook App Secret"
$githubSecretPlain   = Get-SecretPlainText -Secure $GitHubClientSecret   -PromptLabel "GitHub Client Secret"

Write-Host "`nApplying oauth-provider-credentials Secret to namespace '$Namespace'..." -ForegroundColor Cyan

# Use kubectl's --from-literal with --dry-run + apply so it's idempotent
# and the plaintext values never touch disk as a file.
$kubectlArgs = @(
    "create", "secret", "generic", "oauth-provider-credentials",
    "--namespace=$Namespace",
    "--from-literal=GOOGLE_CLIENT_ID=$GoogleClientId",
    "--from-literal=GOOGLE_CLIENT_SECRET=$googleSecretPlain",
    "--from-literal=FACEBOOK_APP_ID=$FacebookAppId",
    "--from-literal=FACEBOOK_APP_SECRET=$facebookSecretPlain",
    "--from-literal=GITHUB_CLIENT_ID=$GitHubClientId",
    "--from-literal=GITHUB_CLIENT_SECRET=$githubSecretPlain",
    "--dry-run=client",
    "-o", "yaml"
)

$yaml = & kubectl @kubectlArgs
$yaml | kubectl apply -f -

# Clear plaintext variables from memory as soon as we're done with them
$googleSecretPlain = $null
$facebookSecretPlain = $null
$githubSecretPlain = $null
[System.GC]::Collect()

Write-Host "`nSecret 'oauth-provider-credentials' applied in namespace '$Namespace'." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Update auth-service / oauth-service / keycloak Deployments to use:" -ForegroundColor Yellow
Write-Host "       envFrom:`n         - secretRef:`n             name: oauth-provider-credentials" -ForegroundColor Gray
Write-Host "  2. Remove any inline GOOGLE_CLIENT_SECRET / FACEBOOK_APP_SECRET / GITHUB_CLIENT_SECRET" -ForegroundColor Yellow
Write-Host "     values still sitting in your Deployment YAML or Kustomize overlays." -ForegroundColor Yellow
Write-Host "  3. Restart the affected pods:" -ForegroundColor Yellow
Write-Host "       kubectl rollout restart deployment/auth-service -n shopno-identity" -ForegroundColor Gray
Write-Host "       kubectl rollout restart deployment/oauth-service -n shopno-identity" -ForegroundColor Gray
Write-Host "       kubectl rollout restart deployment/keycloak -n shopno-identity" -ForegroundColor Gray
