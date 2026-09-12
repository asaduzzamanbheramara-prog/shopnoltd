-- Idempotently provision the databases live-service, meet-service, and
-- messaging-service need. These were referenced in each service's
-- secret.example.yaml DATABASE_URL but never actually created, so the
-- services fail on first connect with "database does not exist" even
-- once their secrets are in place.
SELECT 'CREATE DATABASE live'      WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'live')      \gexec
SELECT 'CREATE DATABASE meet'      WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'meet')      \gexec
SELECT 'CREATE DATABASE messaging' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'messaging') \gexec

GRANT ALL PRIVILEGES ON DATABASE live TO shopno;
GRANT ALL PRIVILEGES ON DATABASE meet TO shopno;
GRANT ALL PRIVILEGES ON DATABASE messaging TO shopno;

\connect live
GRANT USAGE, CREATE ON SCHEMA public TO shopno;

\connect meet
GRANT USAGE, CREATE ON SCHEMA public TO shopno;

\connect messaging
GRANT USAGE, CREATE ON SCHEMA public TO shopno;
