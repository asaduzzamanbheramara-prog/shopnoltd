-- Shopnoltd Database Schema

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(200),
    email VARCHAR(200),
    country VARCHAR(10) DEFAULT 'US',
    kyc_status VARCHAR(20) DEFAULT 'pending',
    kyc_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wallets (
    wallet_id VARCHAR(50) PRIMARY KEY,
    owner_id VARCHAR(50) NOT NULL,
    owner_type VARCHAR(20) DEFAULT 'user',
    currency VARCHAR(10) NOT NULL,
    balance DECIMAL(20, 2) DEFAULT 0,
    available_balance DECIMAL(20, 2) DEFAULT 0,
    pending_balance DECIMAL(20, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_wallets_owner ON wallets(owner_id);
CREATE INDEX idx_wallets_currency ON wallets(currency);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    type VARCHAR(20) NOT NULL,
    wallet_id VARCHAR(50),
    from_wallet VARCHAR(50),
    to_wallet VARCHAR(50),
    amount DECIMAL(20, 2),
    currency VARCHAR(10),
    converted_amount DECIMAL(20, 2),
    from_currency VARCHAR(10),
    to_currency VARCHAR(10),
    exchange_rate DECIMAL(20, 6),
    source VARCHAR(50),
    destination VARCHAR(50),
    description TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    reference VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transactions_wallet ON transactions(wallet_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_created ON transactions(created_at);

CREATE TABLE IF NOT EXISTS exchange_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    wallet_id VARCHAR(50),
    target_wallet_id VARCHAR(50),
    from_currency VARCHAR(10),
    to_currency VARCHAR(10),
    from_amount DECIMAL(20, 2),
    to_amount DECIMAL(20, 2),
    exchange_rate DECIMAL(20, 6),
    fee DECIMAL(20, 2),
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    user_id VARCHAR(50),
    details JSONB,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    plan_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    amount DECIMAL(20, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    trial_end TIMESTAMP,
    current_period_start TIMESTAMP DEFAULT NOW(),
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_alerts (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50),
    user_id VARCHAR(50),
    amount DECIMAL(20, 2),
    risk_score INT,
    risk_level VARCHAR(20),
    flags TEXT,
    country VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO shopnoltd;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO shopnoltd;
