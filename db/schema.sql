CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100),
    email VARCHAR(150),
    role VARCHAR(50) DEFAULT 'user',
    balance DECIMAL(12,6) DEFAULT 0.000000,
    referrer_id INT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    posted_by INT,
    worker_id INT DEFAULT NULL,
    rate DECIMAL(12,6) DEFAULT 0.000000,
    status VARCHAR(50) DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE job_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT,
    user_id INT,
    action VARCHAR(50),
    watch_seconds INT DEFAULT 0,
    rate DECIMAL(12,6) DEFAULT 0.000000,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE platform_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(100),
    amount DECIMAL(12,6),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
