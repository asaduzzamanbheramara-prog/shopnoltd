"""Curated integration directory with honest, action-level readiness labels.

This directory never implies that a provider is connected or executable merely
because it is listed. Runtime provider readiness remains authoritative.
"""
from __future__ import annotations

from typing import Any

# These platforms already have Shopnoltd's authenticated omnichannel API surface.
# They still require valid provider credentials, scopes, account eligibility and
# an enabled/verified action adapter before any external action can run.
EXISTING_OMNICHANNEL_PLATFORMS = frozenset({
    "whatsapp", "facebook", "instagram", "linkedin", "x", "telegram",
    "tiktok", "youtube", "gmail", "outlook", "3cx",
})

# category | slug | display name | connection type | discovery note
_ROWS = [
    ("Commerce", "shopify", "Shopify", "oauth", "Store, products and orders; scopes and app review may apply"),
    ("Commerce", "woocommerce", "WooCommerce", "api_key", "Store REST API; merchant-generated keys required"),
    ("Commerce", "bigcommerce", "BigCommerce", "oauth", "Store APIs and app scopes"),
    ("Commerce", "adobe-commerce", "Adobe Commerce / Magento", "api_key", "REST or GraphQL integration credentials"),
    ("Commerce", "wix", "Wix Stores", "oauth", "Wix app and site permissions"),
    ("Commerce", "squarespace", "Squarespace Commerce", "oauth", "Commerce API access depends on account and scopes"),
    ("Commerce", "webflow", "Webflow Ecommerce", "oauth", "Site and commerce API permissions"),
    ("Commerce", "prestashop", "PrestaShop", "api_key", "Merchant webservice key and enabled resources"),
    ("Commerce", "opencart", "OpenCart", "api_key", "Store API extension and merchant authorization"),
    ("Commerce", "shopware", "Shopware", "oauth", "Integration credentials and permissions"),
    ("Marketplaces", "amazon-seller-central", "Amazon Seller Central (SP-API)", "oauth", "Seller authorization, roles, region and restricted roles"),
    ("Marketplaces", "amazon-ads", "Amazon Ads", "oauth", "Separate Ads API profile and advertiser authorization"),
    ("Marketplaces", "amazon-associates", "Amazon Associates", "api", "Affiliate API eligibility and program compliance"),
    ("Marketplaces", "ebay", "eBay Seller APIs", "oauth", "Developer account, user consent and marketplace scopes"),
    ("Marketplaces", "etsy", "Etsy", "oauth", "Approved app access and shop owner consent"),
    ("Marketplaces", "walmart-marketplace", "Walmart Marketplace", "api_key", "Marketplace partner approval and API credentials"),
    ("Marketplaces", "mercado-libre", "Mercado Libre", "oauth", "Regional developer app and seller authorization"),
    ("Marketplaces", "shopee", "Shopee", "oauth", "Partner platform access and shop authorization"),
    ("Marketplaces", "lazada", "Lazada", "oauth", "Seller center app and regional authorization"),
    ("Marketplaces", "aliexpress", "AliExpress", "oauth", "Affiliate or seller API approval, depending on task"),
    ("Marketplaces", "tiktok-shop", "TikTok Shop", "oauth", "Partner access, seller region and app review"),
    ("Marketplaces", "alibaba-com", "Alibaba.com", "api", "Supplier/buyer API access subject to program approval"),
    ("Affiliate", "affmine", "Affmine", "verify_provider", "Provider identity, official domain and API access must be verified before enabling"),
    ("Affiliate", "awin", "Awin", "oauth", "Advertiser/publisher account and API feature entitlement"),
    ("Affiliate", "shareasale", "ShareASale", "oauth", "Confirm current account/API migration path with Awin"),
    ("Affiliate", "cj-affiliate", "CJ Affiliate", "oauth", "Publisher/advertiser approval and API token"),
    ("Affiliate", "impact", "impact.com", "oauth", "Partner account and API permissions"),
    ("Affiliate", "rakuten-advertising", "Rakuten Advertising", "oauth", "Publisher account and API approval"),
    ("Affiliate", "partnerstack", "PartnerStack", "oauth", "Partner program membership and API access"),
    ("Affiliate", "partnerize", "Partnerize", "oauth", "Partner account and API access"),
    ("Affiliate", "flexoffers", "FlexOffers", "api", "Publisher approval and feed/API access"),
    ("Affiliate", "clickbank", "ClickBank", "api", "Marketplace account and approved API access"),
    ("Affiliate", "admitad", "Admitad", "oauth", "Publisher account and API scopes"),
    ("Affiliate", "skimlinks", "Skimlinks", "api", "Publisher approval and commerce API access"),
    ("Affiliate", "sovrn-commerce", "Sovrn Commerce", "api", "Publisher account and API access"),
    ("Affiliate", "avantlink", "AvantLink", "api", "Affiliate account and API key"),
    ("Affiliate", "tradedoubler", "Tradedoubler", "api", "Partner approval and API credentials"),
    ("Affiliate", "webgains", "Webgains", "api", "Publisher account and API credentials"),
    ("Affiliate", "everflow", "Everflow", "api", "Advertiser/partner account and API key"),
    ("Affiliate", "refersion", "Refersion", "api", "Merchant account and API access"),
    ("Advertising", "google-ads", "Google Ads", "oauth", "Google Ads developer token and customer authorization"),
    ("Advertising", "meta-ads", "Meta Ads", "oauth", "Business verification, app review and ad account permissions"),
    ("Advertising", "tiktok-ads", "TikTok Ads", "oauth", "Marketing API app approval and advertiser access"),
    ("Advertising", "linkedin-ads", "LinkedIn Ads", "oauth", "Marketing Developer Platform access and account roles"),
    ("Advertising", "microsoft-ads", "Microsoft Advertising", "oauth", "Developer token and account authorization"),
    ("Advertising", "pinterest-ads", "Pinterest Ads", "oauth", "Approved app and advertiser permissions"),
    ("Advertising", "reddit-ads", "Reddit Ads", "oauth", "Ads API access and advertiser authorization"),
    ("Advertising", "snapchat-ads", "Snapchat Ads", "oauth", "Marketing API access and organization permissions"),
    ("Advertising", "x-ads", "X Ads", "oauth", "Ads API access is separate from basic X OAuth"),
    ("Advertising", "adsense", "Google AdSense", "oauth", "Publisher account, site review and policy compliance"),
    ("Advertising", "adsterra", "Adsterra", "manual_or_api", "Publisher account and approved placement configuration"),
    ("Advertising", "monetag", "Monetag", "manual_or_api", "Remain disabled until policy, host and provider verification"),
    ("Advertising", "profiton", "ProfitOn", "verify_provider", "Verify provider identity, official integration method and account approval"),
    ("Social & Messaging", "facebook", "Facebook Pages", "oauth", "Existing omnichannel flow; Page scopes and app review required"),
    ("Social & Messaging", "instagram", "Instagram Professional", "oauth", "Existing omnichannel flow; eligible professional account and Meta permissions"),
    ("Social & Messaging", "youtube", "YouTube", "oauth", "Existing omnichannel flow; channel scopes and Google verification"),
    ("Social & Messaging", "tiktok", "TikTok", "oauth", "Existing omnichannel flow; scopes and app review required"),
    ("Social & Messaging", "linkedin", "LinkedIn Pages", "oauth", "Existing omnichannel flow; organization access and product approval"),
    ("Social & Messaging", "x", "X", "oauth", "Existing omnichannel flow; API tier and scopes apply"),
    ("Social & Messaging", "telegram", "Telegram Bot", "bot_token", "Existing bot integration; bot token and user authorization"),
    ("Social & Messaging", "whatsapp", "WhatsApp Business", "business_onboarding", "Existing flow; Meta Business verification and phone onboarding"),
    ("Social & Messaging", "gmail", "Gmail", "oauth", "Existing flow; restricted scopes may require Google verification"),
    ("Social & Messaging", "outlook", "Microsoft Outlook", "oauth", "Existing flow; Microsoft tenant consent and scopes"),
    ("Social & Messaging", "3cx", "3CX", "provider_api", "Existing provider entry; tenant PBX endpoint and credentials required"),
    ("Social & Messaging", "discord", "Discord", "oauth_or_bot", "Bot installation or OAuth scopes and server consent"),
    ("Social & Messaging", "slack", "Slack", "oauth", "Workspace installation and approved scopes"),
    ("Social & Messaging", "twitch", "Twitch", "oauth", "Developer app and broadcaster consent"),
    ("Payments & Finance", "stripe", "Stripe", "oauth", "Connect onboarding, merchant country and platform approval"),
    ("Payments & Finance", "paypal", "PayPal", "oauth", "Business account and REST app credentials"),
    ("Payments & Finance", "paddle", "Paddle", "oauth", "Merchant approval and seller-of-record onboarding"),
    ("Payments & Finance", "lemon-squeezy", "Lemon Squeezy", "api", "Store approval and API key"),
    ("Payments & Finance", "wise", "Wise", "api", "Business account and eligible API access"),
    ("Payments & Finance", "payoneer", "Payoneer", "api", "Partner/API approval; payout capability is not checkout"),
    ("Payments & Finance", "razorpay", "Razorpay", "api", "Merchant onboarding and regional eligibility"),
    ("Payments & Finance", "paystack", "Paystack", "api", "Merchant approval and country eligibility"),
    ("Payments & Finance", "flutterwave", "Flutterwave", "api", "Merchant approval and regional eligibility"),
    ("Payments & Finance", "sslcommerz", "SSLCOMMERZ", "api", "Bangladesh merchant onboarding and credentials"),
    ("Payments & Finance", "bkash", "bKash", "api", "Merchant agreement and production API approval"),
    ("Payments & Finance", "nagad", "Nagad", "api", "Merchant agreement and production API approval"),
    ("CRM & Marketing", "salesforce", "Salesforce", "oauth", "Connected app and org-level scopes"),
    ("CRM & Marketing", "hubspot", "HubSpot", "oauth", "Private/public app scopes and account consent"),
    ("CRM & Marketing", "zoho-crm", "Zoho CRM", "oauth", "Regional Zoho accounts and OAuth scopes"),
    ("CRM & Marketing", "pipedrive", "Pipedrive", "oauth", "App registration and account consent"),
    ("CRM & Marketing", "mailchimp", "Mailchimp", "oauth", "Marketing account and audience permissions"),
    ("CRM & Marketing", "brevo", "Brevo", "api", "Account API key and sender verification"),
    ("CRM & Marketing", "klaviyo", "Klaviyo", "oauth", "Private/public API key and profile consent"),
    ("CRM & Marketing", "activecampaign", "ActiveCampaign", "api", "Account URL and API key"),
    ("Support", "zendesk", "Zendesk", "oauth", "Support account and approved scopes"),
    ("Support", "freshdesk", "Freshdesk", "api", "Support domain and API key"),
    ("Support", "intercom", "Intercom", "oauth", "Workspace installation and scopes"),
    ("Productivity & Files", "google-workspace", "Google Workspace", "oauth", "Per-product scopes and domain-wide delegation policy"),
    ("Productivity & Files", "microsoft-365", "Microsoft 365", "oauth", "Graph permissions and tenant admin consent"),
    ("Productivity & Files", "dropbox", "Dropbox", "oauth", "App registration and user consent"),
    ("Productivity & Files", "notion", "Notion", "oauth", "Workspace integration and page sharing"),
    ("Productivity & Files", "airtable", "Airtable", "oauth", "Base scopes and user consent"),
    ("Productivity & Files", "trello", "Trello", "oauth", "Workspace authorization and board access"),
    ("Productivity & Files", "asana", "Asana", "oauth", "Workspace authorization and scopes"),
    ("Productivity & Files", "clickup", "ClickUp", "oauth", "Workspace authorization and scopes"),
    ("Productivity & Files", "monday", "monday.com", "oauth", "Workspace authorization and scopes"),
    ("Productivity & Files", "box", "Box", "oauth", "Enterprise app approval and scopes"),
    ("Developer & CI", "github", "GitHub", "oauth_or_app", "GitHub App installation or OAuth consent"),
    ("Developer & CI", "gitlab", "GitLab", "oauth", "OAuth app or project access token"),
    ("Developer & CI", "bitbucket", "Bitbucket", "oauth", "Workspace OAuth and repository permissions"),
    ("Developer & CI", "azure-devops", "Azure DevOps", "oauth", "Organization authorization and scopes"),
    ("Developer & CI", "docker-hub", "Docker Hub", "token", "Personal/team token; least-privilege repository access"),
    ("Analytics & SEO", "ga4", "Google Analytics 4", "oauth", "Google Analytics property role and scopes"),
    ("Analytics & SEO", "search-console", "Google Search Console", "oauth", "Verified property ownership and scopes"),
    ("Analytics & SEO", "google-business-profile", "Google Business Profile", "oauth", "Eligible business profile and API access approval"),
    ("Analytics & SEO", "mixpanel", "Mixpanel", "api", "Project token and API entitlement"),
    ("Analytics & SEO", "posthog", "PostHog", "api", "Project API key and host region"),
    ("Analytics & SEO", "semrush", "Semrush", "api", "Paid API units and subscription entitlement"),
    ("Analytics & SEO", "ahrefs", "Ahrefs", "api", "API plan entitlement and usage limits"),
    ("Cloud & Hosting", "aws", "Amazon Web Services", "oauth_or_role", "IAM role or scoped access keys; no root credentials"),
    ("Cloud & Hosting", "azure", "Microsoft Azure", "oauth", "Entra app/service principal and scoped RBAC"),
    ("Cloud & Hosting", "gcp", "Google Cloud", "oauth_or_service_account", "Workload identity or scoped service account"),
    ("Cloud & Hosting", "cloudflare", "Cloudflare", "api_token", "Zone/account-scoped API token"),
    ("Cloud & Hosting", "vercel", "Vercel", "api_token", "Team/project scoped token"),
    ("Cloud & Hosting", "netlify", "Netlify", "oauth_or_token", "Team/site scoped access"),
    ("Cloud & Hosting", "digitalocean", "DigitalOcean", "api_token", "Scoped team token"),
    ("Logistics", "dhl", "DHL", "api", "Business account and regional API approval"),
    ("Logistics", "ups", "UPS", "oauth", "Developer app and shipper account authorization"),
    ("Logistics", "fedex", "FedEx", "oauth", "Developer project and shipper account"),
    ("Logistics", "easypost", "EasyPost", "api", "Account API key and carrier setup"),
    ("Learning & Membership", "teachable", "Teachable", "api", "School plan and API availability"),
    ("Learning & Membership", "thinkific", "Thinkific", "api", "Site plan and API access"),
    ("Learning & Membership", "kajabi", "Kajabi", "api", "Account API access and permissions"),
    ("Learning & Membership", "moodle", "Moodle", "token", "Site administrator enables web services and scoped token"),
]


def _build_entry(row: tuple[str, str, str, str, str]) -> dict[str, Any]:
    category, slug, name, connection_type, note = row
    existing = slug in EXISTING_OMNICHANNEL_PLATFORMS
    return {
        "id": slug,
        "name": name,
        "category": category,
        "connection_type": connection_type,
        "status": "existing_connector_flow" if existing else "catalog_only",
        "executable_actions": [],
        "requires_provider_authorization": True,
        "note": note,
    }


INTEGRATION_CATALOG = tuple(_build_entry(row) for row in _ROWS)


def list_integrations(*, category: str | None = None, query: str | None = None) -> dict[str, Any]:
    """Return a filtered directory; no provider action is triggered here."""
    normalized_category = category.strip().casefold() if category else None
    normalized_query = query.strip().casefold() if query else None
    items = []
    for item in INTEGRATION_CATALOG:
        if normalized_category and item["category"].casefold() != normalized_category:
            continue
        if normalized_query and normalized_query not in " ".join((item["id"], item["name"], item["category"], item["note"])).casefold():
            continue
        items.append(dict(item))
    categories = sorted({item["category"] for item in INTEGRATION_CATALOG})
    return {"total": len(items), "catalog_total": len(INTEGRATION_CATALOG), "categories": categories, "integrations": items}
