<#
Creates Kubernetes secrets from plain-text environment variables or prompts.

Usage examples:
# 1) Export env vars then run (dry-run):
#    $env:STRIPE_SECRET_KEY='sk_test_xxx'; .\scripts\create_k8s_secrets.ps1
# 2) Prompt for values interactively and apply to cluster:
#    .\scripts\create_kobocollect_apk.ps1 -Apply
# 3) Provide values as parameters:
#    .\scripts\create_k8s_secrets.ps1 -StripeSecret 'sk_test_xxx' -Apply
#
# The script by default prints the generated YAML to stdout. Add -Apply to
# run `kubectl apply -f -` and create the secrets in the current cluster.
# Do NOT store plaintext secrets in Git.
#>
param(
    [switch]$Apply,
    [string]$StripeSecret = $env:STRIPE_SECRET_KEY,
    [string]$StripeWebhook = $env:STRIPE_WEBHOOK_SECRET,
    [string]$StripePriceBasic = $env:STRIPE_PRICE_BASIC,
    [string]$StripePricePro = $env:STRIPE_PRICE_PRO,
    [string]$StripePriceEnterprise = $env:STRIPE_PRICE_ENTERPRISE,
    [string]$BillingApiKey = $env:BILLING_API_KEY,
    [string]$FrontendUrl = $env:FRONTEND_URL,
    [string]$PostgresUrl = $env:POSTGRES_URL,
    [string]$PostgresDb = $env:POSTGRES_DB,
    [string]$PostgresUser = $env:POSTGRES_USER,
    [string]$PostgresPassword = $env:POSTGRES_PASSWORD,
    [string]$JwtSecret = $env:JWT_SECRET,
    [string]$SessionSecret = $env:SESSION_SECRET
)

function ToBase64([string]$s) {
    if ([string]::IsNullOrEmpty($s)) { return "" }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    return [Convert]::ToBase64String($bytes)
}

if (-not $StripeSecret) { $StripeSecret = Read-Host -Prompt 'STRIPE_SECRET_KEY (input hidden)' -AsSecureString; $StripeSecret = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($StripeSecret)) }
if (-not $StripeWebhook) { $StripeWebhook = Read-Host 'STRIPE_WEBHOOK_SECRET (plain)' }
if (-not $StripePriceBasic) { $StripePriceBasic = Read-Host 'STRIPE_PRICE_BASIC (plain)' }
if (-not $StripePricePro) { $StripePricePro = Read-Host 'STRIPE_PRICE_PRO (plain)' }
if (-not $StripePriceEnterprise) { $StripePriceEnterprise = Read-Host 'STRIPE_PRICE_ENTERPRISE (plain)' }
if (-not $BillingApiKey) { $BillingApiKey = Read-Host 'BILLING_API_KEY (plain)' }
if (-not $FrontendUrl) { $FrontendUrl = Read-Host 'FRONTEND_URL (e.g. https://shopnoltd.dpdns.org)' }
if (-not $PostgresUrl) { $PostgresUrl = Read-Host 'POSTGRES_URL (plain)' }
if (-not $PostgresDb) { $PostgresDb = Read-Host 'POSTGRES_DB (plain)' }
if (-not $PostgresUser) { $PostgresUser = Read-Host 'POSTGRES_USER (plain)' }
if (-not $PostgresPassword) { $PostgresPassword = Read-Host -Prompt 'POSTGRES_PASSWORD (input hidden)' -AsSecureString; $PostgresPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($PostgresPassword)) }
if (-not $JwtSecret) { $JwtSecret = Read-Host -Prompt 'JWT_SECRET (input hidden)' -AsSecureString; $JwtSecret = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($JwtSecret)) }
if (-not $SessionSecret) { $SessionSecret = Read-Host -Prompt 'SESSION_SECRET (input hidden)' -AsSecureString; $SessionSecret = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($SessionSecret)) }

$yaml = @"
apiVersion: v1
kind: Secret
metadata:
  name: oauth-secrets
type: Opaque
data:
  JWT_SECRET: $(ToBase64 $JwtSecret)
  SESSION_SECRET: $(ToBase64 $SessionSecret)
---
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
type: Opaque
data:
  POSTGRES_DB: $(ToBase64 $PostgresDb)
  POSTGRES_PASSWORD: $(ToBase64 $PostgresPassword)
  POSTGRES_USER: $(ToBase64 $PostgresUser)
---
apiVersion: v1
kind: Secret
metadata:
  name: stripe-secret
type: Opaque
data:
  STRIPE_SECRET_KEY: $(ToBase64 $StripeSecret)
  STRIPE_WEBHOOK_SECRET: $(ToBase64 $StripeWebhook)
  STRIPE_PRICE_BASIC: $(ToBase64 $StripePriceBasic)
  STRIPE_PRICE_PRO: $(ToBase64 $StripePricePro)
  STRIPE_PRICE_ENTERPRISE: $(ToBase64 $StripePriceEnterprise)
  BILLING_API_KEY: $(ToBase64 $BillingApiKey)
  FRONTEND_URL: $(ToBase64 $FrontendUrl)
  POSTGRES_URL: $(ToBase64 $PostgresUrl)
"@

Write-Output "# Generated Kubernetes secrets YAML (sensitive)"
Write-Output $yaml

if ($Apply) {
    Write-Output "Applying secrets to Kubernetes cluster..."
    $proc = Start-Process -FilePath kubectl -ArgumentList @('apply','-f','-') -NoNewWindow -RedirectStandardInput 'pipe' -RedirectStandardOutput 'pipe' -RedirectStandardError 'pipe' -PassThru
    $proc.StandardInput.Write($yaml)
    $proc.StandardInput.Close()
    $out = $proc.StandardOutput.ReadToEnd()
    $err = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    Write-Output $out
    if ($err) { Write-Error $err }
}
else {
    Write-Output "Run with -Apply to write these secrets to the cluster (kubectl required)."
}
