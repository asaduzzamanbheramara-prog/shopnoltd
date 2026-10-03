-- Durable advertising campaign funding saga.
-- This file is executed as a separate psql invocation from 018, so explicitly
-- select the dedicated ads database before referencing its campaign tables.
\connect ads

-- Payment-service debit is idempotent; this record lets ad-service safely resume after crashes.
CREATE TABLE IF NOT EXISTS campaign_fundings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id uuid NOT NULL UNIQUE REFERENCES campaigns(id) ON DELETE RESTRICT,
  advertiser_user_id text NOT NULL,
  amount_minor bigint NOT NULL CHECK (amount_minor > 0),
  currency char(3) NOT NULL,
  payment_id uuid,
  idempotency_key text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','charged','failed','refunded')),
  error_detail text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_campaign_fundings_status ON campaign_fundings(status);
