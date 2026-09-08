-- Customer-initiated payment idempotency.
-- Safe for existing transactions: historical rows keep NULL keys.
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128);

CREATE UNIQUE INDEX IF NOT EXISTS uq_transaction_deposit_idempotency
    ON transactions (tenant_id, user_id, type, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
