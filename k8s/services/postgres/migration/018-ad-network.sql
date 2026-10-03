-- Shopnoltd-owned advertising network database and schema.
-- Idempotent: safe for repeated GitOps migration-hook execution.
SELECT 'CREATE DATABASE ads'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ads') \gexec

\connect ads

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS advertisers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id text NOT NULL,
  legal_name text NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','suspended','rejected')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_advertisers_owner ON advertisers(owner_user_id);

CREATE TABLE IF NOT EXISTS publishers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id text NOT NULL,
  display_name text NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','suspended','rejected')),
  revenue_share_bps integer NOT NULL DEFAULT 7000 CHECK (revenue_share_bps BETWEEN 0 AND 10000),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_publishers_owner ON publishers(owner_user_id);

CREATE TABLE IF NOT EXISTS publisher_sites (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  publisher_id uuid NOT NULL REFERENCES publishers(id) ON DELETE RESTRICT,
  domain text NOT NULL,
  verification_method text NOT NULL DEFAULT 'pending',
  verification_status text NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','verified','failed')),
  verification_token text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(publisher_id, domain)
);

CREATE TABLE IF NOT EXISTS ad_zones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id uuid NOT NULL REFERENCES publisher_sites(id) ON DELETE RESTRICT,
  name text NOT NULL,
  width integer NOT NULL CHECK (width > 0 AND width <= 4096),
  height integer NOT NULL CHECK (height > 0 AND height <= 4096),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(site_id, name)
);

CREATE TABLE IF NOT EXISTS campaigns (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  advertiser_id uuid NOT NULL REFERENCES advertisers(id) ON DELETE RESTRICT,
  name text NOT NULL,
  pricing_model text NOT NULL CHECK (pricing_model IN ('CPM','CPC','CPA','FLAT')),
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','pending','approved','active','paused','completed','rejected')),
  starts_at timestamptz NOT NULL,
  ends_at timestamptz NOT NULL,
  budget_minor bigint NOT NULL CHECK (budget_minor >= 0),
  spent_minor bigint NOT NULL DEFAULT 0 CHECK (spent_minor >= 0),
  target_cpm_minor bigint CHECK (target_cpm_minor IS NULL OR target_cpm_minor >= 0),
  target_cpc_minor bigint CHECK (target_cpc_minor IS NULL OR target_cpc_minor >= 0),
  target_cpa_minor bigint CHECK (target_cpa_minor IS NULL OR target_cpa_minor >= 0),
  currency char(3) NOT NULL DEFAULT 'USD',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (ends_at > starts_at),
  CHECK (spent_minor <= budget_minor)
);
CREATE INDEX IF NOT EXISTS idx_campaigns_delivery ON campaigns(status, starts_at, ends_at);

CREATE TABLE IF NOT EXISTS creatives (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id uuid NOT NULL REFERENCES campaigns(id) ON DELETE RESTRICT,
  name text NOT NULL,
  asset_url text NOT NULL,
  click_url text NOT NULL,
  width integer NOT NULL CHECK (width > 0 AND width <= 4096),
  height integer NOT NULL CHECK (height > 0 AND height <= 4096),
  mime_type text NOT NULL CHECK (mime_type IN ('image/jpeg','image/png','image/webp','text/html')),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','blocked')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_creatives_campaign ON creatives(campaign_id, status);

CREATE TABLE IF NOT EXISTS campaign_targeting (
  campaign_id uuid PRIMARY KEY REFERENCES campaigns(id) ON DELETE CASCADE,
  countries text[] NOT NULL DEFAULT '{}',
  languages text[] NOT NULL DEFAULT '{}',
  devices text[] NOT NULL DEFAULT '{}',
  domains text[] NOT NULL DEFAULT '{}',
  frequency_cap integer CHECK (frequency_cap IS NULL OR frequency_cap > 0)
);

CREATE TABLE IF NOT EXISTS ad_deliveries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id text NOT NULL,
  site_id uuid NOT NULL REFERENCES publisher_sites(id) ON DELETE RESTRICT,
  zone_id uuid NOT NULL REFERENCES ad_zones(id) ON DELETE RESTRICT,
  campaign_id uuid NOT NULL REFERENCES campaigns(id) ON DELETE RESTRICT,
  creative_id uuid NOT NULL REFERENCES creatives(id) ON DELETE RESTRICT,
  token_hash text NOT NULL UNIQUE,
  served_at timestamptz NOT NULL DEFAULT now(),
  impression_at timestamptz,
  click_at timestamptz,
  conversion_at timestamptz,
  charged_minor bigint NOT NULL DEFAULT 0 CHECK (charged_minor >= 0),
  publisher_earning_minor bigint NOT NULL DEFAULT 0 CHECK (publisher_earning_minor >= 0)
);
CREATE INDEX IF NOT EXISTS idx_deliveries_request ON ad_deliveries(request_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_campaign ON ad_deliveries(campaign_id, served_at);

CREATE TABLE IF NOT EXISTS ad_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  delivery_id uuid NOT NULL REFERENCES ad_deliveries(id) ON DELETE RESTRICT,
  event_key text NOT NULL,
  event_type text NOT NULL CHECK (event_type IN ('impression','click','conversion')),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(delivery_id, event_key)
);

CREATE TABLE IF NOT EXISTS fraud_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  delivery_id uuid REFERENCES ad_deliveries(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  reason text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS publisher_payouts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  publisher_id uuid NOT NULL REFERENCES publishers(id) ON DELETE RESTRICT,
  period_start date NOT NULL,
  period_end date NOT NULL,
  amount_minor bigint NOT NULL CHECK (amount_minor >= 0),
  currency char(3) NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','paid','held','rejected')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(publisher_id, period_start, period_end)
);

CREATE OR REPLACE VIEW delivery_reporting AS
SELECT c.id AS campaign_id, c.advertiser_id, p.id AS publisher_id,
       d.site_id, d.zone_id, count(*) AS deliveries,
       count(*) FILTER (WHERE d.impression_at IS NOT NULL) AS impressions,
       count(*) FILTER (WHERE d.click_at IS NOT NULL) AS clicks,
       count(*) FILTER (WHERE d.conversion_at IS NOT NULL) AS conversions,
       coalesce(sum(d.charged_minor),0) AS charged_minor,
       coalesce(sum(d.publisher_earning_minor),0) AS publisher_earning_minor
FROM ad_deliveries d
JOIN campaigns c ON c.id=d.campaign_id
JOIN publisher_sites s ON s.id=d.site_id
JOIN publishers p ON p.id=s.publisher_id
GROUP BY c.id,c.advertiser_id,p.id,d.site_id,d.zone_id;
