"""Labels that free-subdomain users must never be given.

A free label is also used as the user's mailbox local part, so this set covers
platform hostnames (taken from the k8s ingress hosts) and the mailbox names
reserved by RFC 2142 and common mail practice.
"""

# Keep in sync with the ingress hosts under k8s/.
# tests/test_reserved_labels.py fails if a host is missing here.
_PLATFORM_HOSTS = (
    "www mail api admin shopno shopnoltd ns1 ns2 mx ftp static cdn "
    "admin-infrastructure admin-portal ai-platform analytics-service "
    "android-gateway android argocd audit-service auth-service auth keycloak "
    "billing payment exchange chatwoot chat code codeserver code-server "
    "devices domain enketo event exchange-service foundation freedomain "
    "gateway gitea grafana interior kobotoolbox kobo license-service "
    "mail-api minio mobile-api n8n notification-service oauth-service "
    "openai owncast live payment-service postgres redis remote remote-engine "
    "report-service sessions shopnoltdandroid social social-service "
    "storage-service tenant-router training vpn webmail web-portal "
    "worker-service alertmanager cursor jitsi-jicofo jitsi-jvb jitsi-prosody "
    "jitsi-web kf loki onlyoffice scheduler-service shopnoltdpc "
    "mail-server mail-service roundcube smtp imap pop pop3 autoconfig "
    "autodiscover mta-sts ns dns"
)

_MAILBOX_ROLES = (
    "postmaster abuse hostmaster webmaster noc security info sales support "
    "marketing usenet news uucp root mailer-daemon nobody noreply no-reply "
    "administrator"
)

RESERVED = frozenset(_PLATFORM_HOSTS.split()) | frozenset(_MAILBOX_ROLES.split())
