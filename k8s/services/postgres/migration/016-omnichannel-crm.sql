\connect social
-- Shopnoltd Omnichannel CRM / n8n contract
-- Idempotent DDL. Apply through the owning deployment migration process.
-- Secrets/tokens are references only; never store raw provider tokens here.

CREATE TABLE IF NOT EXISTS social_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  platform VARCHAR(32) NOT NULL,
  account_type VARCHAR(32) NOT NULL DEFAULT 'user',
  platform_account_id VARCHAR(255) NOT NULL,
  username VARCHAR(255),
  display_name VARCHAR(255),
  status VARCHAR(24) NOT NULL DEFAULT 'pending',
  scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
  access_token_ref VARCHAR(255),
  refresh_token_ref VARCHAR(255),
  token_expires_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  connected_at TIMESTAMPTZ,
  last_sync_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, platform, platform_account_id)
);

CREATE TABLE IF NOT EXISTS client_platform_identity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  client_id VARCHAR(128),
  connection_id UUID REFERENCES social_connections(id) ON DELETE SET NULL,
  platform VARCHAR(32) NOT NULL,
  platform_user_id VARCHAR(255) NOT NULL,
  username VARCHAR(255),
  display_name VARCHAR(255),
  profile_url TEXT,
  phone VARCHAR(64),
  email VARCHAR(320),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, platform, platform_user_id, connection_id)
);

CREATE INDEX IF NOT EXISTS ix_client_platform_identity_client
  ON client_platform_identity (tenant_id, client_id);

CREATE UNIQUE INDEX IF NOT EXISTS ux_client_platform_identity_unlinked
  ON client_platform_identity (tenant_id, platform, platform_user_id)
  WHERE connection_id IS NULL;

CREATE TABLE IF NOT EXISTS client_conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  client_id VARCHAR(128),
  connection_id UUID REFERENCES social_connections(id) ON DELETE SET NULL,
  platform VARCHAR(32) NOT NULL,
  platform_conversation_id VARCHAR(255),
  status VARCHAR(24) NOT NULL DEFAULT 'open',
  subject TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_message_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, platform, connection_id, platform_conversation_id)
);

CREATE TABLE IF NOT EXISTS client_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  conversation_id UUID REFERENCES client_conversations(id) ON DELETE SET NULL,
  client_id VARCHAR(128),
  connection_id UUID REFERENCES social_connections(id) ON DELETE SET NULL,
  platform VARCHAR(32) NOT NULL,
  platform_user_id VARCHAR(255),
  direction VARCHAR(8) NOT NULL CHECK (direction IN ('in','out')),
  message_type VARCHAR(32) NOT NULL DEFAULT 'text',
  message_text TEXT,
  platform_message_id VARCHAR(255),
  reply_to_platform_message_id VARCHAR(255),
  media JSONB NOT NULL DEFAULT '[]'::jsonb,
  raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  delivery_status VARCHAR(24),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, platform, connection_id, platform_message_id)
);

CREATE TABLE IF NOT EXISTS client_inbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  client_id VARCHAR(128),
  platform VARCHAR(32) NOT NULL,
  platform_user_id VARCHAR(255),
  direction VARCHAR(8) NOT NULL CHECK (direction IN ('in','out')),
  message_text TEXT,
  platform_message_id VARCHAR(255),
  raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, platform, platform_message_id)
);

CREATE INDEX IF NOT EXISTS ix_client_inbox_client_time
  ON client_inbox (tenant_id, client_id, created_at DESC);

CREATE TABLE IF NOT EXISTS platform_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  connection_id UUID REFERENCES social_connections(id) ON DELETE SET NULL,
  client_id VARCHAR(128),
  platform VARCHAR(32) NOT NULL,
  action VARCHAR(64) NOT NULL,
  target_type VARCHAR(32),
  target_id VARCHAR(255),
  status VARCHAR(24) NOT NULL DEFAULT 'queued',
  idempotency_key VARCHAR(255),
  request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_code VARCHAR(128),
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS platform_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  connection_id UUID REFERENCES social_connections(id) ON DELETE SET NULL,
  client_id VARCHAR(128),
  platform VARCHAR(32) NOT NULL,
  platform_post_id VARCHAR(255),
  source_post_id VARCHAR(128),
  status VARCHAR(24) NOT NULL DEFAULT 'draft',
  content TEXT NOT NULL,
  media JSONB NOT NULL DEFAULT '[]'::jsonb,
  scheduled_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, platform, connection_id, platform_post_id)
);

CREATE TABLE IF NOT EXISTS platform_sync_errors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  connection_id UUID REFERENCES social_connections(id) ON DELETE SET NULL,
  platform VARCHAR(32) NOT NULL,
  workflow_name VARCHAR(255) NOT NULL,
  http_status INTEGER,
  error_body TEXT,
  payload_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS automation_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  name VARCHAR(255) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  trigger JSONB NOT NULL DEFAULT '{}'::jsonb,
  conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
  actions JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS automation_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  rule_id UUID REFERENCES automation_rules(id) ON DELETE SET NULL,
  trigger_event JSONB NOT NULL DEFAULT '{}'::jsonb,
  status VARCHAR(24) NOT NULL DEFAULT 'queued',
  result JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_message TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS platform_capabilities (
  platform VARCHAR(32) NOT NULL,
  action VARCHAR(64) NOT NULL,
  availability VARCHAR(24) NOT NULL DEFAULT 'provider_dependent',
  requires_oauth BOOLEAN NOT NULL DEFAULT TRUE,
  notes TEXT,
  PRIMARY KEY (platform, action)
);

INSERT INTO platform_capabilities(platform, action, availability, requires_oauth, notes) VALUES
('whatsapp','send_message','supported',TRUE,'WhatsApp Business/Cloud API and approved messaging rules apply'),
('whatsapp','receive_message','supported',TRUE,'Webhook subscription required'),
('facebook','send_message','provider_dependent',TRUE,'Messenger/Page permissions required'),
('facebook','create_post','provider_dependent',TRUE,'Page publishing permissions required'),
('instagram','send_message','provider_dependent',TRUE,'Professional account and messaging permissions required'),
('instagram','create_post','provider_dependent',TRUE,'Professional account/content publishing permissions required'),
('linkedin','create_post','provider_dependent',TRUE,'Member/organization permissions and product access required'),
('linkedin','comment','provider_dependent',TRUE,'API permissions and target permissions required'),
('x','create_post','provider_dependent',TRUE,'Current X API access/tier required'),
('telegram','send_message','supported',TRUE,'Bot must have access to target chat/channel'),
('youtube','create_post','provider_dependent',TRUE,'YouTube Data API and channel authorization required'),
('youtube','comment','provider_dependent',TRUE,'YouTube Data API and channel authorization required'),
('youtube','live','provider_dependent',TRUE,'YouTube Live Streaming API required'),
('tiktok','create_post','provider_dependent',TRUE,'Content Posting API access/approval required'),
('gmail','send_message','supported',TRUE,'Gmail API OAuth scope required'),
('outlook','send_message','supported',TRUE,'Microsoft Graph delegated/application permissions required'),
('3cx','call','provider_dependent',TRUE,'3CX Call Control/API access required')
ON CONFLICT (platform, action) DO UPDATE SET
  availability=EXCLUDED.availability,
  requires_oauth=EXCLUDED.requires_oauth,
  notes=EXCLUDED.notes;
