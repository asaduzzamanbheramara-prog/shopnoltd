// Canonical website-creation type catalog. Existing types are preserved; new types are additive.
export const WEBSITE_TYPES = [
  {
    id: 'ecommerce',
    name: 'E-commerce',
    description: 'Online store with products, catalog, cart, checkout and customer accounts.',
    capabilities: ['catalog', 'cart', 'checkout', 'orders', 'customers'],
  },
  {
    id: 'blog',
    name: 'Blog',
    description: 'Publishing website for articles, authors, categories, media and SEO.',
    capabilities: ['posts', 'authors', 'categories', 'media', 'seo'],
  },
  {
    id: 'portfolio',
    name: 'Portfolio',
    description: 'Showcase website for projects, services, case studies and contact details.',
    capabilities: ['projects', 'case-studies', 'services', 'contact'],
  },
  {
    id: 'business',
    name: 'Business',
    description: 'General business website for company information, services, leads and pages.',
    capabilities: ['pages', 'services', 'leads', 'contact', 'seo'],
  },
  {
    id: 'pos',
    name: 'POS',
    description: 'Point-of-sale website/application for products, sales, inventory and customers.',
    capabilities: ['products', 'sales', 'inventory', 'customers', 'reports'],
  },
  {
    id: 'pos_billing',
    name: 'POS Billing System',
    description: 'Dedicated POS billing system for invoices, receipts, payments, stock and cashier workflows.',
    capabilities: ['billing', 'invoices', 'receipts', 'payments', 'inventory', 'cashier', 'reports'],
  },
  {
    id: 'hr',
    name: 'HR',
    description: 'Human resources website/application for employees, attendance, leave and payroll workflows.',
    capabilities: ['employees', 'attendance', 'leave', 'payroll', 'performance', 'reports'],
  },
  {
    id: 'erp',
    name: 'ERP',
    description: 'Enterprise resource planning website/application spanning core business operations.',
    capabilities: ['finance', 'inventory', 'sales', 'purchasing', 'hr', 'reporting'],
  },
  {
    id: 'website',
    name: 'Website',
    description: 'General-purpose website with configurable pages, content, navigation and branding.',
    capabilities: ['pages', 'content', 'navigation', 'branding', 'seo'],
  },
]

export const WEBSITE_TYPE_BY_ID = Object.fromEntries(WEBSITE_TYPES.map((type) => [type.id, type]))
