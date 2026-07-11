# Shopnoltd Kubernetes Secret Generator
# Secrets must come from environment variables or GitHub Actions secrets.
# NEVER commit Stripe keys into this repository.

$jwt = [guid]::NewGuid().ToString()
$sess = [guid]::NewGuid().ToString()
$pgpass = [guid]::NewGuid().ToString()


$stripeSecret = $env:STRIPE_SECRET
$stripeWebhook = $env:STRIPE_WEBHOOK
$stripePriceBasic = $env:STRIPE_PRICE_BASIC
$stripePricePro = $env:STRIPE_PRICE_PRO
$stripePriceEnterprise = $env:STRIPE_PRICE_ENTERPRISE
$billingApiKey = $env:BILLING_API_KEY


if (-not $stripeSecret) {
    Write-Error "Missing STRIPE_SECRET environment variable"
    exit 1
}

if (-not $stripeWebhook) {
    Write-Error "Missing STRIPE_WEBHOOK environment variable"
    exit 1
}


Write-Output "Generating Shopnoltd Kubernetes secrets..."


$helper = Join-Path `
    -Path $PSScriptRoot `
    -ChildPath "create_k8s_secrets.ps1"


& $helper `
    -StripeSecret $stripeSecret `
    -StripeWebhook $stripeWebhook `
    -StripePriceBasic $stripePriceBasic `
    -StripePricePro $stripePricePro `
    -StripePriceEnterprise $stripePriceEnterprise `
    -BillingApiKey $billingApiKey `
    -FrontendUrl "https://shopnoltd.dpdns.org" `
    -PostgresUrl "postgres://shopnoltd:$pgpass@postgres:5432/shopnoltd" `
    -PostgresDb "shopnoltd" `
    -PostgresUser "shopnoltd" `
    -PostgresPassword $pgpass `
    -JwtSecret $jwt `
    -SessionSecret $sess `
    -Apply
