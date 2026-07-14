#!/bin/bash
# Applies every fix from this conversation directly to the correct paths.
# Run from the repo root: bash apply-fixes.sh
set -e

echo "Removing committed third-party APK (if present)..."
git rm --cached APKPure_3.20.7402_apkpure.com.apk 2>/dev/null || true
rm -f APKPure_3.20.7402_apkpure.com.apk

echo "Writing .gitignore..."
cat > .gitignore << 'GITIGNORE_EOF'
###################################
# Environment and secrets
###################################

.env
.env.*
!.env.example
*.secret
*secret*.yaml
secrets.yaml
secrets-actual.yaml
config/secrets.yaml
cloudflared/
*.json.cred


###################################
# Database files
###################################

*.sql
*.dump


###################################
# Python
###################################

__pycache__/
*.py[cod]
*.pyo
venv/
.venv/


###################################
# Node / Frontend
###################################

node_modules/
dist/
build/


###################################
# Docker
###################################

*.tar
*.tar.gz


###################################
# Kubernetes local files
###################################

kubectl


###################################
# APK files
###################################

apks/*.apk


###################################
# IDE
###################################

.vscode/
.idea/


###################################
# OS
###################################

.DS_Store
Thumbs.db


###################################
# Generated reports
###################################

*-REPORT.*
*-report-*.txt
check-results-*.txt
FINAL_*.txt
COMPLETE_*.txt
SYSTEM_*.html
branding-*-report-*.txt


###################################
# Temporary files
###################################

*.log
*.tmp
*.bak

kc-current-state-backup.yaml

# Kubernetes binaries
kubectl

# Docker
*.tar
*.tar.gz

# Environment
.env
.env.*
!.env.example

# Build files
node_modules/
__pycache__/
*.pyc


# Python environments
.venv/
venv/
env/

# Python cache
__pycache__/
*.pyc

# AI data
*/logs/
*/uploads/
*/vectorstore/

release-assets/
*.exe
APKPure_3.20.7402_apkpure.com.apk
GITIGNORE_EOF

echo "Writing .env.example..."
cat > .env.example << 'ENV_EOF'
# Copy this file to .env for local development:
#   cp .env.example .env
# docker-compose.yml requires a .env file to exist (env_file: [.env]) even
# if you leave every value at its default below.

# ---------- shared infra credentials ----------
POSTGRES_PASSWORD=changeme
MINIO_ROOT_USER=shopno
MINIO_ROOT_PASSWORD=changeme123

# ---------- auth / oauth ----------
JWT_SECRET=dev-only-change-me
SESSION_SECRET=dev-only-change-me
KEYCLOAK_ADMIN_PASSWORD=CHANGE_ME

# ---------- payment-service (leave blank for local/demo mode) ----------
# Any gateway left blank runs the payment-service in demo mode; nothing is
# faked as "live" data. Fill in real sandbox keys only when you need to test
# an actual payment provider.
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
PAYPAL_CLIENT_ID=
PAYPAL_SECRET=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
SSLCOMMERZ_STORE_ID=
SSLCOMMERZ_STORE_PASSWORD=
BKASH_APP_KEY=
BKASH_APP_SECRET=
NAGAD_MERCHANT_ID=
NAGAD_MERCHANT_KEY=
ENV_EOF

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Writing docker-compose.yml..."
cat > docker-compose.yml << 'COMPOSE_EOF'
# Shopno Ltd — core platform compose
# This wires up the services that already have real code in platform/*.
# Services that only contain a Dockerfile stub (e.g. api-service, tenant-router)
# are intentionally left out until they have real app code — see README.

services:

  # ---------- shared infra ----------
  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: shopno
      POSTGRES_USER: shopno
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      # One DB per service — created automatically on first boot by the
      # init script below (only runs against an empty pgdata volume).
      POSTGRES_MULTIPLE_DATABASES: gateway,auth,oauth,domains,payments,storage
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/postgres-init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shopno"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    restart: unless-stopped
    ports:
      - "6379:6379"

  minio:
    image: minio/minio:latest
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-shopno}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-changeme123}
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # console
    volumes:
      - miniodata:/data

  # ---------- core services (prebuilt images from GHCR) ----------
  gateway:
    image: ghcr.io/asaduzzamanbheramara-prog/shopnoltd/gateway:latest
    restart: unless-stopped
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+asyncpg://shopno:${POSTGRES_PASSWORD:-changeme}@postgres:5432/gateway
      REDIS_URL: redis://redis:6379/0
      CORS_ORIGINS: http://localhost:3100,http://localhost:3101
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  auth-service:
    image: ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:latest
    restart: unless-stopped
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+asyncpg://shopno:${POSTGRES_PASSWORD:-changeme}@postgres:5432/auth
      REDIS_URL: redis://redis:6379/0
      CORS_ORIGINS: http://localhost:3100,http://localhost:3101
    ports:
      - "8081:8080"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  oauth-service:
    image: ghcr.io/asaduzzamanbheramara-prog/shopnoltd/oauth-service:latest
    restart: unless-stopped
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+asyncpg://shopno:${POSTGRES_PASSWORD:-changeme}@postgres:5432/oauth
      REDIS_URL: redis://redis:6379/0
      CORS_ORIGINS: http://localhost:3100,http://localhost:3101
    ports:
      - "3001:3000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  domain-service:
    image: ghcr.io/asaduzzamanbheramara-prog/shopnoltd/domain-service:latest
    restart: unless-stopped
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+asyncpg://shopno:${POSTGRES_PASSWORD:-changeme}@postgres:5432/domains
      REDIS_URL: redis://redis:6379/0
      CORS_ORIGINS: http://localhost:3100,http://localhost:3101
    ports:
      - "8082:8080"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    # NOTE: also needs a PowerDNS instance reachable via POWERDNS_API_URL — not
    # included here yet, see README "Known gaps".

  payment-service:
    image: ghcr.io/asaduzzamanbheramara-prog/shopnoltd/payment-service:latest
    restart: unless-stopped
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+asyncpg://shopno:${POSTGRES_PASSWORD:-changeme}@postgres:5432/payments
      REDIS_URL: redis://redis:6379/0
      CORS_ORIGINS: http://localhost:3100,http://localhost:3101
    ports:
      - "8083:8080"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  storage-service:
    image: ghcr.io/asaduzzamanbheramara-prog/shopnoltd/storage-service:latest
    restart: unless-stopped
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+asyncpg://shopno:${POSTGRES_PASSWORD:-changeme}@postgres:5432/storage
      REDIS_URL: redis://redis:6379/0
      CORS_ORIGINS: http://localhost:3100,http://localhost:3101
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER:-shopno}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-changeme123}
    ports:
      - "8084:8080"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      minio:
        condition: service_started

  # ---------- frontends ----------
  admin-portal:
    image: ghcr.io/asaduzzamanbheramara-prog/shopnoltd/admin-portal:latest
    restart: unless-stopped
    ports:
      - "3100:3000"
    depends_on: [gateway]

  web-portal:
    image: ghcr.io/asaduzzamanbheramara-prog/shopnoltd/web-portal:latest
    restart: unless-stopped
    ports:
      - "3101:3000"
    depends_on: [gateway]

volumes:
  pgdata:
  miniodata:
COMPOSE_EOF

echo "Writing scripts/postgres-init/init-multiple-dbs.sh..."
mkdir -p scripts/postgres-init
cat > scripts/postgres-init/init-multiple-dbs.sh << 'INIT_EOF'
#!/bin/bash
# Creates one Postgres database per microservice on first container start.
# Triggered automatically by the official postgres image via
# /docker-entrypoint-initdb.d/*.sh — only runs against an empty data volume.
set -e
set -u

function create_database() {
  local database=$1
  echo "Creating database '$database'"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE $database'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
}

if [ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
  echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
  for db in $(echo "$POSTGRES_MULTIPLE_DATABASES" | tr ',' ' '); do
    create_database "$db"
  done
  echo "Multiple databases created"
fi
INIT_EOF
chmod +x scripts/postgres-init/init-multiple-dbs.sh

echo "Writing shared/libraries/python/__init__.py..."
mkdir -p shared/libraries/python
cat > shared/libraries/python/__init__.py << 'SHARED_EOF'
"""Placeholder for shared Python utilities across shopnoltd services.

Every platform/*/Dockerfile does `COPY shared/libraries/python /app/shared`,
but no service currently imports anything from it (verified: no
`from shared` / `import shared` in any service's app code). This stub only
exists so `docker compose build` (and CI) doesn't fail on a missing COPY
source.

If/when you actually build shared logging, auth helpers, etc. meant to be
reused across services, put it here.
"""
SHARED_EOF

echo "Writing .github/workflows/build-platform.yml..."
mkdir -p .github/workflows
cat > .github/workflows/build-platform.yml << 'WORKFLOW_EOF'
name: Build platform images
on:
  push:
    branches: [main]
    paths:
      - 'platform/**'
      - 'shared/**'
      - '.github/workflows/build-platform.yml'
  workflow_dispatch:
env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ${{ github.repository_owner }}/shopnoltd
jobs:
  build:
    name: Build ${{ matrix.service }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - { service: domain-service,        dockerfile: platform/domain-service/Dockerfile }
          - { service: interior-service,      dockerfile: platform/interior-service/Dockerfile }
          - { service: event-service,         dockerfile: platform/event-service/Dockerfile }
          - { service: foundation-service,    dockerfile: platform/foundation-service/Dockerfile }
          - { service: training-service,      dockerfile: platform/training-service/Dockerfile }
          - { service: freedomain-service,    dockerfile: platform/freedomain-service/Dockerfile }
          - { service: api-service,         dockerfile: platform/api-service/Dockerfile }
          - { service: gateway,            dockerfile: platform/gateway/Dockerfile }
          - { service: oauth-service,      dockerfile: platform/oauth-service/Dockerfile }
          - { service: tenant-router,      dockerfile: platform/tenant-router/Dockerfile }
          - { service: billing-engine,     dockerfile: platform/billing-engine/Dockerfile }
          - { service: analytics-service,  dockerfile: platform/analytics-service/Dockerfile }
          - { service: search-service,     dockerfile: platform/search-service/Dockerfile }
          - { service: storage-service,    dockerfile: platform/storage-service/Dockerfile }
          - { service: notification-service,dockerfile: platform/notification-service/Dockerfile }
          - { service: scheduler-service,  dockerfile: platform/scheduler-service/Dockerfile }
          - { service: worker-service,     dockerfile: platform/worker-service/Dockerfile }
          - { service: payment-service,    dockerfile: platform/payment-service/Dockerfile }
          - { service: exchange-service,   dockerfile: platform/exchange-service/Dockerfile }
          - { service: auth-service,       dockerfile: platform/auth-service/Dockerfile }
          - { service: audit-service,      dockerfile: platform/audit-service/Dockerfile }
          - { service: report-service,     dockerfile: platform/report-service/Dockerfile }
          - { service: license-service,    dockerfile: platform/license-service/Dockerfile }
          - { service: mobile-api,         dockerfile: platform/mobile-api/Dockerfile }
          - { service: ai-platform,        dockerfile: platform/ai-platform/Dockerfile }
          - { service: admin-portal,       dockerfile: platform/admin-portal/Dockerfile }
          - { service: web-portal,         dockerfile: platform/web-portal/Dockerfile }
          - { service: android-portal,     dockerfile: platform/android-portal/Dockerfile }
          - { service: pc-portal,          dockerfile: platform/pc-portal/Dockerfile }
          - { service: messaging-service,  dockerfile: platform/messaging-service/Dockerfile }
          - { service: meet-service,       dockerfile: platform/meet-service/Dockerfile }
          - { service: live-service,       dockerfile: platform/live-service/Dockerfile }
          - { service: mail-service,       dockerfile: platform/mail-service/Dockerfile }
          - { service: social-service,     dockerfile: platform/social-service/Dockerfile }
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Skip if Dockerfile missing
        id: check
        run: '[ -f "${{ matrix.dockerfile }}" ] && echo "skip=false" >> "$GITHUB_OUTPUT" || echo "skip=true" >> "$GITHUB_OUTPUT"'
      - name: Login to GHCR
        if: steps.check.outputs.skip == 'false'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Set up Docker Buildx
        if: steps.check.outputs.skip == 'false'
        uses: docker/setup-buildx-action@v3
      - name: Build & push
        if: steps.check.outputs.skip == 'false'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ${{ matrix.dockerfile }}
          push: true
          tags: |
            ghcr.io/${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:latest
            ghcr.io/${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
WORKFLOW_EOF

echo ""
echo "Done. Verifying key files landed in the right place:"
echo "---"
find shared -type f
find scripts/postgres-init -type f
ls .github/workflows/build-platform.yml
ls .env.example .gitignore
echo "---"
echo "Now review with 'git status', then:"
echo "  git add -A"
echo "  git commit -m 'Fix local dev stack, add shared/libraries/python stub, fix CI trigger paths'"
echo "  git push"
