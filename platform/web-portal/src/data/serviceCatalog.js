const SERVICE = (icon, name, description, url, category = 'Platform') => ({
  icon,
  name,
  description,
  url,
  category,
})

export const SERVICES = [
  SERVICE('🌐', 'Domain Registration', "Register a real domain through Shopnoltd's registrar service.", '/domain-registration', 'Platform'),
  SERVICE('🧰', 'ShopnoltdToolbox', 'KoboToolbox-powered data collection and forms.', 'https://kobo.shopnoltd.dpdns.org', 'Productivity'),
  SERVICE('💬', 'Chat & Support', 'Customer conversations, team messaging and support workflows.', 'https://chat.shopnoltd.dpdns.org', 'Communication'),
  SERVICE('🔴', 'Live Streaming', 'Self-hosted live streaming and creator workflows.', 'https://live.shopnoltd.dpdns.org', 'Media'),
  SERVICE('☁️', 'Cloud Storage', 'Cloud files, objects and storage workflows.', '/dashboard', 'Productivity'),
  SERVICE('✉️', 'Mail', 'Shopnoltd mailbox, email and notification workflows.', '/dashboard', 'Communication'),
  SERVICE('💳', 'Billing & Subscriptions', 'Plans, subscriptions, invoices, wallets and billing operations.', 'https://billing.shopnoltd.dpdns.org', 'Business'),
  SERVICE('💰', 'Payments & Wallet', 'Payment methods, deposits, transactions and wallet operations.', 'https://shopnoltd.dpdns.org/wallet', 'Business'),
  SERVICE('💱', 'Exchange', 'Supported currency/exchange operations and rates.', 'https://exchange.shopnoltd.dpdns.org', 'Business'),
  SERVICE('🤖', 'AI Workspace', 'Shopnoltd AI services, model routing and automation.', 'https://ai-platform.shopnoltd.dpdns.org', 'AI'),
  SERVICE('💻', 'Code Server', 'Browser-based development environment.', 'https://code-server.shopnoltd.dpdns.org', 'Developer'),
  SERVICE('🦊', 'Git', 'Git repositories and collaborative source control.', 'https://gitea.shopnoltd.dpdns.org', 'Developer'),
  SERVICE('🔗', 'API', 'Platform APIs for applications, services, automation and integrations.', 'https://api.shopnoltd.dpdns.org/openapi.json', 'Developer'),
  SERVICE('📊', 'User Dashboard', 'Manage your account, services, subscriptions and connected workflows.', '/dashboard', 'Platform'),
  SERVICE('⚡', 'Automation', 'Automate workflows, notifications and actions between supported services.', 'https://n8n.shopnoltd.dpdns.org', 'Automation'),
  SERVICE('📝', 'Forms & Enketo', 'Form collection and browser-based form workflows.', 'https://enketo.shopnoltd.dpdns.org', 'Productivity'),
  SERVICE('💬', 'Chatwoot', 'Customer inbox, support conversations and communication automation.', 'https://chatwoot.shopnoltd.dpdns.org', 'Communication'),
  SERVICE('📱', 'Remote Access', 'Shopnoltd remote-device workspace for authorized device support and control.', 'https://remote.shopnoltd.dpdns.org', 'Remote Access'),
  SERVICE('🖥️', 'Device Console', 'Browse registered devices and launch authorized remote sessions.', 'https://devices.shopnoltd.dpdns.org', 'Remote Access'),
]

export const CONNECTED_PLATFORMS = [
  SERVICE('🌐', 'Web & Websites', 'Organize Shopnoltd websites, web apps and connected services.', '/dashboard', 'Connected'),
  SERVICE('👤', 'Profiles & Accounts', 'Manage personal, creator, developer and business profiles.', '/dashboard', 'Connected'),
  SERVICE('📧', 'Email & Notifications', 'Connect email, notification and messaging workflows.', '/dashboard', 'Connected'),
  SERVICE('💬', 'WhatsApp', 'Connect WhatsApp messaging through an authorized provider/API.', 'https://n8n.shopnoltd.dpdns.org', 'Social & Messaging'),
  SERVICE('✈️', 'Telegram', 'Connect Telegram bots/channels through authorized integrations.', 'https://n8n.shopnoltd.dpdns.org', 'Social & Messaging'),
  SERVICE('💬', 'Messenger', 'Connect Facebook Messenger through an authorized integration.', 'https://n8n.shopnoltd.dpdns.org', 'Social & Messaging'),
  SERVICE('📷', 'Instagram', 'Connect Instagram publishing and messaging where supported by the official API.', 'https://n8n.shopnoltd.dpdns.org', 'Social & Messaging'),
  SERVICE('📘', 'Facebook', 'Connect Facebook pages, publishing and messaging where authorized.', 'https://n8n.shopnoltd.dpdns.org', 'Social & Messaging'),
  SERVICE('💼', 'LinkedIn', 'Connect LinkedIn publishing and organization workflows where authorized.', 'https://n8n.shopnoltd.dpdns.org', 'Social & Messaging'),
  SERVICE('𝕏', 'X', 'Connect X publishing and automation where authorized by the platform API.', 'https://n8n.shopnoltd.dpdns.org', 'Social & Messaging'),
  SERVICE('🎵', 'TikTok', 'Connect TikTok publishing and automation where supported by the official API.', 'https://n8n.shopnoltd.dpdns.org', 'Social & Messaging'),
  SERVICE('▶️', 'YouTube', 'Connect channels, publishing, comments and creator workflows through authorized APIs.', 'https://n8n.shopnoltd.dpdns.org', 'Video & Social'),
  SERVICE('📺', 'Video & Live', 'Manage live streaming and video workflows.', 'https://live.shopnoltd.dpdns.org', 'Video & Social'),
  SERVICE('⚡', 'Automation Hub', 'Central workflow automation for mail, messaging, social, billing and service events.', 'https://n8n.shopnoltd.dpdns.org', 'Automation'),
]

export const ADMIN_SERVICES = [
  SERVICE('🛡️', 'Platform Admin', 'Unified administration for users, tenants, services, database operations, reports and platform controls.', 'https://admin.shopnoltd.dpdns.org', 'Administration'),
  SERVICE('🗄️', 'Database & Tables', 'Browse and manage authorized database tables and rows with RBAC/audit controls.', '/admin', 'Administration'),
  SERVICE('📊', 'Reports & Analytics', 'Generate, review and publish platform reports and operational analytics.', '/admin', 'Administration'),
  SERVICE('🧊', '3D / HD / 4K Visualization', 'Interactive service topology and visualization workspace for platform operations.', '/admin', 'Visualization'),
  SERVICE('💳', 'Billing Administration', 'Manage plans, subscriptions, invoices and billing operations.', 'https://billing.shopnoltd.dpdns.org', 'Finance'),
  SERVICE('💰', 'Payment Administration', 'Manage payment transactions, deposits, wallets and provider operations.', 'https://shopnoltd.dpdns.org/admin', 'Finance'),
  SERVICE('💱', 'Exchange Administration', 'Manage exchange/rate workflows and supported financial operations.', 'https://exchange.shopnoltd.dpdns.org', 'Finance'),
  SERVICE('📡', 'Remote Device Administration', 'Manage authorized remote-device services and sessions.', 'https://devices.shopnoltd.dpdns.org', 'Remote Access'),
  SERVICE('🔧', 'GitOps / Deployment', 'Authorized deployment and synchronization control through ArgoCD.', 'https://argocd.shopnoltd.dpdns.org', 'Infrastructure'),
]
