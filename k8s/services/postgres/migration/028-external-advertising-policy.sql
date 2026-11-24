-- Central, exact-host external ad-network controls. New hosts are disabled until an
-- administrator explicitly enables only the networks approved for that host.
\connect ads

CREATE TABLE IF NOT EXISTS external_ad_policies (
  hostname text PRIMARY KEY,
  enabled boolean NOT NULL DEFAULT false,
  networks jsonb NOT NULL DEFAULT '{"adsense":false,"adsterra":false,"monetag":false,"profiton":false}'::jsonb,
  placements jsonb NOT NULL DEFAULT '{"home":false,"services":false,"blog":false,"feed":false,"downloads":false}'::jsonb,
  updated_by text NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (hostname = lower(hostname)),
  CHECK (hostname !~ '[^a-z0-9.-]')
);

CREATE TABLE IF NOT EXISTS external_ad_policy_audit (
  id bigserial PRIMARY KEY,
  hostname text NOT NULL,
  actor_user_id text NOT NULL,
  enabled boolean NOT NULL,
  networks jsonb NOT NULL,
  placements jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_external_ad_policy_audit_host_time
  ON external_ad_policy_audit(hostname, created_at DESC);

-- Preserve current apex-host integrations only. Other hosts remain disabled.
INSERT INTO external_ad_policies(hostname, enabled, networks, placements, updated_by)
VALUES (
  'shopnoltd.dpdns.org',
  true,
  '{"adsense":true,"adsterra":true,"monetag":false,"profiton":true}'::jsonb,
  '{"home":true,"services":true,"blog":true,"feed":true,"downloads":true}'::jsonb,
  'migration:028'
)
ON CONFLICT (hostname) DO NOTHING;
