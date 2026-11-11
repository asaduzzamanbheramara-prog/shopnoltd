"""Central database-control-plane capability registry.

The registry is intentionally declarative. It does not grant database access;
owning services remain responsible for authentication, tenant scoping,
validation, audit logging and execution of every operation.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.database_control_plane.contract import (
    DatabaseCapability,
    DatabaseTableCapability,
    DatastoreKind,
    DdlCapabilities,
)


def _table(name: str, *, readable: bool = False, writable: bool = False,
           bulk: bool = False, importable: bool = False, exportable: bool = False,
           reportable: bool = False, destructive: bool = False,
           protected: str | None = None, tenant_scoped: bool = False,
           ddl: DdlCapabilities = DdlCapabilities.NONE) -> DatabaseTableCapability:
    """Declare schema metadata without granting generic row access by default."""
    return DatabaseTableCapability(
        name=name,
        readable=readable,
        writable=writable,
        bulk_write=bulk,
        importable=importable,
        exportable=exportable,
        reportable=reportable,
        destructive=destructive,
        protected_reason=protected,
        tenant_scoped=tenant_scoped,
        ddl=ddl,
    )


DATABASE_CAPABILITIES: tuple[DatabaseCapability, ...] = (
    DatabaseCapability(
        service="ad-service", database="ads", schemas=("public",),
        tables=(
            _table("advertisers", protected="Advertiser ownership and approval are service-owned.", tenant_scoped=True),
            _table("publishers", protected="Publisher ownership and revenue share are service-owned.", tenant_scoped=True),
            _table("publisher_sites", protected="Site verification is service-owned.", tenant_scoped=True),
            _table("ad_zones", protected="Inventory authorization is service-owned.", tenant_scoped=True),
            _table("campaigns", protected="Campaign budgets and financial state are service-owned.", tenant_scoped=True),
            _table("creatives", protected="Creative moderation and destination validation are service-owned.", tenant_scoped=True),
            _table("campaign_targeting", protected="Campaign targeting is service-owned.", tenant_scoped=True),
            _table("campaign_fundings", protected="Funding ledger is financial and service-owned.", tenant_scoped=True),
            _table("ad_deliveries", protected="Delivery ledger is append-only and service-owned.", tenant_scoped=True),
            _table("ad_events", protected="Event ledger is append-only and service-owned.", tenant_scoped=True),
            _table("fraud_events", protected="Fraud and security history is append-only.", tenant_scoped=True),
            _table("publisher_payouts", protected="Payout state is financial and service-owned.", tenant_scoped=True),
        ),
        protected_reason="Advertising inventory, delivery and financial events require validated ad-service APIs.",
    ),
    DatabaseCapability(
        service="api-service", database="shopnoltd", schemas=("public",),
        tables=(
            _table("works", protected="Work lifecycle is API-service validated.", tenant_scoped=True),
            _table("work_assignments", protected="Worker assignments are transactional and service-owned.", tenant_scoped=True),
            _table("work_events", protected="Work event history is append-only and service-owned.", tenant_scoped=True),
            _table("work_evidence", protected="Evidence may contain private URLs and user-submitted material.", tenant_scoped=True),
            _table("work_ratings", protected="Worker ratings are service-owned.", tenant_scoped=True),
            _table("work_sessions", protected="Work sessions and timing are service-owned.", tenant_scoped=True),
            _table("work_submissions", protected="Work submissions require validation and audit.", tenant_scoped=True),
            _table("work_task_configs", protected="Task configuration is service-owned.", tenant_scoped=True),
            _table("global_task_rates", protected="Global task rates affect financial calculations.", tenant_scoped=True),
            _table("referral_codes", protected="Referral attribution is service-owned.", tenant_scoped=True),
            _table("referral_policies", protected="Referral policy changes affect financial rewards.", tenant_scoped=True),
            _table("referral_rewards", protected="Referral rewards are financial state.", tenant_scoped=True),
            _table("referral_system_identities", protected="System identity mapping is security-sensitive.", tenant_scoped=True),
            _table("referrals", protected="Referral attribution and settlement are service-owned.", tenant_scoped=True),
        ),
        protected_reason="Core work, referral and task-rate records are managed through validated API-service operations.",
    ),
    DatabaseCapability(
        service="payment-service", database="payments", schemas=("public",),
        tables=(
            _table("wallets", protected="Wallet balances and frozen funds are changed only by validated wallet APIs.", tenant_scoped=True),
            _table("transactions", protected="Money-moving transactions are changed only by validated payment APIs.", tenant_scoped=True),
            _table("webhook_events", protected="Webhook idempotency and security state is service-owned."),
            _table("admin_audit_log", protected="Payment audit history is append-only."),
            _table("direct_payment_accounts", protected="Direct payment account identifiers are restricted.", tenant_scoped=True),
            _table("payment_accounts", protected="Payment account private values and routing are restricted.", tenant_scoped=True),
            _table("direct_payment_intents", protected="Payment intents are transactional state.", tenant_scoped=True),
            _table("direct_payment_submissions", protected="Payment evidence is verification-owned.", tenant_scoped=True),
            _table("alembic_version", protected="Migration metadata is deployment-owned."),
        ),
        protected_reason="Financial state must remain behind validated payment-service APIs.",
    ),
    DatabaseCapability(
        service="exchange-service", database="payments", schemas=("public",),
        tables=(
            _table("rates", protected="Exchange rates are owned by the rate updater."),
            _table("conversions", protected="Conversion history is financial and audit state.", tenant_scoped=True),
        ),
        protected_reason="Exchange-rate and conversion data are service-owned.",
    ),
    DatabaseCapability(
        service="social-service", database="social", schemas=("public",),
        tables=(
            _table("posts", protected="Social posts are tenant-scoped service data.", tenant_scoped=True),
            _table("blog_posts", protected="Blog content is managed through the audited blog API.", tenant_scoped=True),
            _table("blog_likes", protected="Blog engagement records are service-owned.", tenant_scoped=True),
            _table("blog_comments", protected="Blog comments are service-owned.", tenant_scoped=True),
            _table("blog_shares", protected="Blog share records are service-owned.", tenant_scoped=True),
            _table("blog_saved_posts", protected="Saved blog posts are user-scoped service data.", tenant_scoped=True),
            _table("likes", protected="Social engagement records are service-owned.", tenant_scoped=True),
            _table("saved_posts", protected="Saved social posts are user-scoped service data.", tenant_scoped=True),
            _table("reactions", protected="Social reactions are service-owned.", tenant_scoped=True),
            _table("shares", protected="Social share records are service-owned.", tenant_scoped=True),
            _table("follows", protected="Follow relationships are service-owned.", tenant_scoped=True),
            _table("comments", protected="Social comments are service-owned.", tenant_scoped=True),
            _table("blog_admin_audit", protected="Blog administration audit history is append-only.", tenant_scoped=True),
            _table("post_views", protected="Post view telemetry is service-owned.", tenant_scoped=True),
            _table("social_connections", protected="Social account connections and credentials are restricted.", tenant_scoped=True),
            _table("client_platform_identity", protected="External platform identity mapping is service-owned.", tenant_scoped=True),
            _table("client_conversations", protected="External conversations may contain private messages.", tenant_scoped=True),
            _table("client_inbox", protected="Omnichannel inbox state is service-owned.", tenant_scoped=True),
            _table("client_messages", protected="Omnichannel message content is private service data.", tenant_scoped=True),
            _table("omnichannel_oauth_tokens", protected="OAuth tokens are security-sensitive.", tenant_scoped=True),
            _table("platform_actions", protected="Platform actions are audited service operations.", tenant_scoped=True),
            _table("platform_capabilities", protected="Platform capability metadata is service-owned."),
            _table("platform_posts", protected="External platform posts are service-owned.", tenant_scoped=True),
            _table("platform_sync_errors", protected="Synchronization error history is service-owned.", tenant_scoped=True),
            _table("automation_rules", protected="Automation rules are service-owned.", tenant_scoped=True),
            _table("automation_runs", protected="Automation execution history is service-owned.", tenant_scoped=True),
            _table("social_automation_schedules", protected="Social publishing schedules require tenant and owner validation.", tenant_scoped=True),
            _table("social_post_drafts", protected="Social post drafts and approvals are user-scoped workflow data.", tenant_scoped=True),
        ),
        protected_reason="Social, blog and omnichannel records require tenant-scoped service validation and audit.",
    ),
    DatabaseCapability(
        service="kobotoolbox", database="formhub", kind=DatastoreKind.MONGODB,
        tables=(
            _table("instances", protected="Kobo submissions remain behind Kobo validation and audit flows."),
        ),
        tenant_scope="service",
        protected_reason="Kobo MongoDB data is application-owned; generic row access and mutation are disabled.",
    ),
    DatabaseCapability(
        service="oauth-service", database="oauth", schemas=("public",),
        tables=(
            _table("users", protected="Identity mirror is service-owned.", tenant_scoped=True),
            _table("user_profiles", protected="Profiles are managed through profile APIs.", tenant_scoped=True),
            _table("kyc_identities", protected="Government identity and KYC material is restricted.", tenant_scoped=True),
            _table("imported_workbooks", protected="Import manifests are importer-owned."),
            _table("imported_excel_rows", protected="Imported source records are restricted."),
            _table("secret_vault_entries", protected="Encrypted secrets are vault-owned; generic row access is disabled."),
            _table("tenants", protected="Tenant provisioning and plan state are service-owned."),
            _table("customers", protected="Customer identity and billing profile data is restricted.", tenant_scoped=True),
            _table("account_provisioning_jobs", protected="Provisioning jobs are durable service-owned state.", tenant_scoped=True),
        ),
        protected_reason="Identity, KYC, profile and encrypted imported-account data remain service-owned.",
    ),
    DatabaseCapability(
        service="ai-platform", database="ai", schemas=("public",),
        tables=(
            _table("ai_providers", protected="Provider API keys are encrypted and managed only by AI service APIs."),
            _table("ai_models", protected="Model routing and provider relationships are service-owned."),
            _table("ai_connections", protected="Encrypted connection secrets are vault-owned."),
            _table("documents", protected="Uploaded document text is private tenant data.", tenant_scoped=True),
            _table("chunks", protected="Document chunks and embeddings are private tenant data.", tenant_scoped=True),
            _table("agents", protected="Agent prompts and configuration are service-owned.", tenant_scoped=True),
            _table("ai_conversations", protected="AI conversation content is private tenant data.", tenant_scoped=True),
        ),
        protected_reason="AI provider secrets, documents and conversations are managed through validated AI APIs.",
    ),
    DatabaseCapability(service="auth-service", database="auth", schemas=("public",),
        tables=(_table("sessions", protected="Authentication sessions are security-sensitive."),),
        protected_reason="Authentication session records are not exposed through generic row access."),
    DatabaseCapability(service="mobile-api", database="mobile", schemas=("public",),
        tables=(
            _table("app_releases", protected="Release metadata and artifact references are deployment-owned."),
            _table("app_config", protected="Mobile client configuration is service-owned."),
        )),
    DatabaseCapability(service="meet-service", database="meet", schemas=("public",),
        tables=(
            _table("rooms", protected="Meeting room access and passwords are service-owned.", tenant_scoped=True),
            _table("room_participants", protected="Meeting participant records are private.", tenant_scoped=True),
            _table("call_sessions", protected="Call session state is service-owned.", tenant_scoped=True),
        )),
    DatabaseCapability(service="mail-service", database="mail", schemas=("public",),
        tables=(
            _table("domains", protected="Mail domain provisioning is service-owned.", tenant_scoped=True),
            _table("mailboxes", protected="Mailbox ownership and quota are service-owned.", tenant_scoped=True),
            _table("mail_messages", protected="Email message content is private.", tenant_scoped=True),
        )),
    DatabaseCapability(service="live-service", database="live", schemas=("public",),
        tables=(_table("streams", protected="Stream ownership and live state are service-owned.", tenant_scoped=True),)),
    DatabaseCapability(service="tenant-router", database="router", schemas=("public",),
        tables=(_table("tenant_routes", protected="Tenant routing and namespace mapping are security-sensitive.", tenant_scoped=True),)),
    DatabaseCapability(service="event-service", database="events", schemas=("public",),
        tables=(
            _table("events", protected="Event ownership and capacity are service-owned.", tenant_scoped=True),
            _table("event_sessions", protected="Event session scheduling is service-owned.", tenant_scoped=True),
            _table("event_tickets", protected="Ticket and attendee records are private.", tenant_scoped=True),
            _table("event_speakers", protected="Speaker profile data is service-owned.", tenant_scoped=True),
        )),
    DatabaseCapability(service="report-service", database="reports", schemas=("public",),
        tables=(_table("reports", protected="Report queries and generated file paths are service-owned.", tenant_scoped=True),)),
    DatabaseCapability(service="worker-service", database="worker", schemas=("public",),
        tables=(_table("tasks", protected="Worker task arguments and results are service-owned."),)),
    DatabaseCapability(service="domain-service", database="domains", schemas=("public",),
        tables=(
            _table("zones", protected="DNS zone ownership and configuration are service-owned.", tenant_scoped=True),
            _table("records", protected="DNS record changes require domain-service validation.", tenant_scoped=True),
            _table("registrars", protected="Registrar API key and secret fields must not be exposed; migrate credentials to secret references."),
            _table("domains", protected="Purchased domain ownership and expiry are service-owned.", tenant_scoped=True),
        ),
        protected_reason="Domain provisioning is service-owned; registrar credential storage requires a separate security fix.",
    ),
    DatabaseCapability(service="storage-service", database="storage", schemas=("public",),
        tables=(
            _table("buckets", protected="Tenant storage quotas and bucket ownership are service-owned.", tenant_scoped=True),
            _table("objects", protected="Object metadata and storage paths are service-owned.", tenant_scoped=True),
            _table("profile_videos", protected="Published profile media is service-owned.", tenant_scoped=True),
            _table("profile_video_uploads", protected="Upload session metadata is service-owned.", tenant_scoped=True),
            _table("professional_profiles", protected="Professional profile data is tenant-scoped.", tenant_scoped=True),
        )),
    DatabaseCapability(service="license-service", database="licenses", schemas=("public",),
        tables=(_table("licenses", protected="License keys and entitlements are security-sensitive.", tenant_scoped=True),)),
    DatabaseCapability(service="interior-service", database="interior", schemas=("public",),
        tables=(
            _table("interior_projects", protected="Interior project records are tenant-scoped.", tenant_scoped=True),
            _table("interior_models", protected="3D model storage paths are service-owned.", tenant_scoped=True),
            _table("interior_rooms", protected="Room geometry and furniture configuration are service-owned.", tenant_scoped=True),
        )),
    DatabaseCapability(service="analytics-service", database="analytics", schemas=("public",),
        tables=(_table("events", protected="Analytics events may contain user activity data.", tenant_scoped=True),)),
    DatabaseCapability(service="foundation-service", database="foundation", schemas=("public",),
        tables=(
            _table("donors", protected="Donor identity and contact information is restricted.", tenant_scoped=True),
            _table("donations", protected="Donation and payment records are financial data.", tenant_scoped=True),
            _table("campaigns", protected="Fundraising campaign state is service-owned.", tenant_scoped=True),
            _table("grants", protected="Grant and funder information is service-owned.", tenant_scoped=True),
            _table("beneficiaries", protected="Beneficiary identity and aid records are restricted.", tenant_scoped=True),
        )),
    DatabaseCapability(service="audit-service", database="audit", schemas=("public",),
        tables=(_table("audit_logs", protected="Audit history is append-only and security-sensitive.", tenant_scoped=True),)),
    DatabaseCapability(service="freedomain-service", database="freedomain", schemas=("public",),
        tables=(_table("freedomain", protected="Free-domain ownership and provisioning are service-owned.", tenant_scoped=True),)),
    DatabaseCapability(service="keycloak", database="keycloak", schemas=("public",),
        protected_reason="Identity, credentials, sessions and realm state are Keycloak-owned."),
    DatabaseCapability(service="chatwoot", database="chatwoot_production", schemas=("public",),
        protected_reason="Support conversations and customer data are Chatwoot-owned."),
    DatabaseCapability(service="kobotoolbox-kc", database="kobocat", schemas=("public",),
        protected_reason="KoboCAT form and submission data is application-owned."),
    DatabaseCapability(service="kobotoolbox-kpi", database="kpi", schemas=("public",),
        protected_reason="Kobo KPI reporting and user data is application-owned."),
    DatabaseCapability(service="litellm-proxy", database="litellm", schemas=("public",),
        protected_reason="LLM proxy keys, usage and model metadata are service-owned."),
    DatabaseCapability(service="notification-service", database="notifications", schemas=("public",),
        tables=(
            _table("notifications", protected="Notification recipients and content are private.", tenant_scoped=True),
            _table("templates", protected="Notification templates are service-owned."),
        )),
    DatabaseCapability(service="session-manager", database="session_manager", schemas=("public",),
        tables=(
            _table("proxies", protected="Proxy credentials are encrypted and must not be exposed."),
            _table("profiles", protected="Browser profile ownership and storage paths are private."),
        )),
    DatabaseCapability(service="training-service", database="training", schemas=("public",),
        tables=(
            _table("courses", protected="Course and instructor records are service-owned.", tenant_scoped=True),
            _table("lessons", protected="Lesson content is service-owned."),
            _table("enrollments", protected="Learner enrollment and progress are private.", tenant_scoped=True),
            _table("quizzes", protected="Assessment content is service-owned."),
            _table("quiz_attempts", protected="Assessment answers and results are private.", tenant_scoped=True),
            _table("certificates", protected="Certificate issuance records are service-owned.", tenant_scoped=True),
        )),
)


def catalog() -> list[dict[str, Any]]:
    """Return a JSON-safe capability catalog for authorized admin clients."""
    return [
        {
            "service": capability.service,
            "database": capability.database,
            "kind": capability.kind.value,
            "schemas": list(capability.schemas),
            "backup": capability.backup,
            "restore": capability.restore,
            "database_ddl": capability.database_ddl.value,
            "tenant_scope": capability.tenant_scope,
            "protected_reason": capability.protected_reason,
            "tables": [asdict(table) | {"ddl": table.ddl.value} for table in capability.tables],
        }
        for capability in DATABASE_CAPABILITIES
    ]
