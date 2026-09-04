export const BLOG_POSTS = [
  {
    slug: 'building-shopnoltd-as-a-unified-platform',
    title: 'Building Shopnoltd as a Unified Platform',
    excerpt: 'How Shopnoltd brings domains, data collection, automation, development and business services together in one platform.',
    publishedAt: '2026-09-04',
    category: 'Platform',
    author: 'Shopnoltd',
    content: [
      'Shopnoltd is designed as a unified platform rather than a collection of disconnected tools. The goal is to give users one place to discover services, authenticate once and move between connected workflows.',
      'The platform brings together domain services, data collection, automation, development, AI, billing and operational services while keeping service boundaries explicit.',
      'We are continuing to improve the public portal, administration experience and service integrations so that every published capability has a clear, working path from the user interface to its backend service.',
    ],
  },
  {
    slug: 'one-dashboard-for-connected-services',
    title: 'One Dashboard for Connected Services',
    excerpt: 'A single account experience for managing connected Shopnoltd services and workflows.',
    publishedAt: '2026-09-04',
    category: 'Product',
    author: 'Shopnoltd',
    content: [
      'A central dashboard makes it easier to move between services without losing the context of your Shopnoltd account.',
      'The web portal is being developed around authenticated service access, protected financial operations and role-aware administration.',
      'As more integrations become production-ready, the dashboard will become the central launch point for those workflows.',
    ],
  },
  {
    slug: 'automation-and-ai-workflows',
    title: 'Automation and AI Workflows',
    excerpt: 'Connecting automation and AI capabilities to practical platform workflows.',
    publishedAt: '2026-09-04',
    category: 'AI & Automation',
    author: 'Shopnoltd',
    content: [
      'Automation is most useful when it connects real platform events to useful actions. Shopnoltd is building toward that model with workflow automation and AI services.',
      'The architecture separates the user-facing portal from service-specific backends so integrations can be enabled, monitored and secured independently.',
      'Future updates will expand model management, workflow orchestration and service-to-service automation while preserving authentication and audit boundaries.',
    ],
  },
]

export function getBlogPost(slug) {
  return BLOG_POSTS.find((post) => post.slug === slug) || null
}
