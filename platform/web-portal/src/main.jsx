import React, { useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Pricing from './pages/Pricing'
import Privacy from './pages/Privacy'
import About from './pages/About'
import Contact from './pages/Contact'
import Terms from './pages/Terms'
import Login from './pages/Login'
import Register from './pages/Register'
import Callback from './pages/Callback'
import Dashboard from './pages/Dashboard'
import AIWorkspace from './pages/AIWorkspace'
import AIConnections from './pages/AIConnections'
import AIModels from './pages/AIModels'
import OmnichannelConnections from './pages/OmnichannelConnections'
import ProtectedRoute from './components/ProtectedRoute'
import Blog from './pages/Blog'
import BlogAdmin from './pages/BlogAdmin'
import MyBlog from './pages/MyBlog'
import BlogPost from './pages/BlogPost'
import Plugins from './pages/Plugins'
import Services from './pages/Services'
import Downloads from './pages/Downloads'
import Phone from './pages/Phone'
import DomainRegistration from './pages/DomainRegistration'
import VPN from './pages/VPN'
import DomainManagement from './pages/DomainManagement'
import AdminDashboard from './pages/AdminDashboard'
import AdminInfrastructure from './pages/AdminInfrastructure'
import AdminProfileVideos from './pages/AdminProfileVideos'
import PaymentAccountsAdmin from './pages/PaymentAccountsAdmin'
import DatabaseControlPlane from './pages/DatabaseControlPlaneFull'
import TaskRatesAdmin from './pages/TaskRatesAdmin'
import AdminRoute from './components/AdminRoute'
import FinancialCenter from './pages/FinancialCenter'
import CheckoutCurrencySafe from './pages/CheckoutCurrencySafe'
import CheckoutComplete from './pages/CheckoutComplete'
import SocialFeed from './pages/SocialFeed'
import PostDetail from './pages/PostDetail'
import WorkHub, { WorkDetail } from './pages/WorkHub'
import ReferralHub from './pages/ReferralHub'
import ReferralAdmin from './pages/ReferralAdmin'
import AccountHub from './pages/AccountHub'
import Discover from './pages/Discover'
import WebsiteBuilder from './pages/WebsiteBuilder'
import Profiles from './pages/Profiles'
import PublicProfiles from './pages/PublicProfiles'
import DataManagementProfile from './pages/DataManagementProfile'
import InteriorBusinessProfile from './pages/InteriorBusinessProfile'
import { isPlatformAdmin } from './lib/jwt'
import AdminAnalytics from './pages/AdminAnalytics'
import Affiliate from './pages/Affiliate'
import AdNetwork from './pages/AdNetwork'
import { trackPageView } from './lib/analytics'

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {})
  })
}

function InstallPrompt() {
  const [prompt, setPrompt] = React.useState(null)
  React.useEffect(() => {
    const handler = (event) => {
      event.preventDefault()
      setPrompt(event)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])
  if (!prompt) return null
  return <button type="button" onClick={async () => { await prompt.prompt(); setPrompt(null) }} style={{ color: 'white', background: 'rgba(255,255,255,0.14)', border: '1px solid rgba(255,255,255,0.5)', borderRadius: 6, padding: '5px 12px', cursor: 'pointer', whiteSpace: 'nowrap' }}>Install Shopnoltd</button>
}

const PUBLIC_LINKS = [['About', '/about'], ['Services', '/services'], ['Pricing', '/pricing'], ['Profiles', '/profiles'], ['Interior', '/profile/interior-business'], ['VPN', '/vpn'], ['Create Website', '/create-website'], ['Discover', '/discover'], ['Feed', '/feed'], ['Work', '/work'], ['Blog', '/blog'], ['AI', '/ai'], ['Services', '/services'], ['Phone', '/phone'], ['Domains', '/domain-registration'], ['Downloads', '/downloads'], ['Affiliate & Tools', '/affiliate'], ['Android Cloud', '/android-cloud'], ['Contact', '/contact']]
const STANDALONE_APP_PATHS = new Set(['/android-cloud'])

function Nav() {
  const navigate = useNavigate(); const location = useLocation(); const token = localStorage.getItem('shopno_token'); const loggedIn = !!token; const isAdmin = loggedIn && isPlatformAdmin()
  function handleLogout() { localStorage.removeItem('shopno_token'); localStorage.removeItem('shopno_refresh_token'); sessionStorage.removeItem('shopno_profile_provisioned'); navigate('/') }
  function renderPublicLink(label, path) {
    const style = { color: 'white', textDecoration: 'none', padding: '6px 2px', whiteSpace: 'nowrap', fontWeight: location.pathname === path ? 700 : 400 }
    return STANDALONE_APP_PATHS.has(path)
      ? <a key={path} href={path} style={style}>{label}</a>
      : <Link key={path} to={path} style={style}>{label}</Link>
  }
  return <nav style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 12, padding: '12px clamp(14px, 3vw, 24px)', background: '#0ea5e9', color: 'white', boxSizing: 'border-box' }}>
    <Link to="/" style={{ color: 'white', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 20, textDecoration: 'none', whiteSpace: 'nowrap', marginRight: 'auto' }}><img src="/logo.svg" alt="Shopnoltd" style={{ height: 28, width: 28, objectFit: 'contain' }} />Shopnoltd</Link>
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'flex-end', gap: '8px 16px', minWidth: 0 }}>
      {PUBLIC_LINKS.map(([label, path]) => renderPublicLink(label, path))}
      <InstallPrompt />
      {!loggedIn && <><Link to="/login" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Login</Link><Link to="/register" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Register</Link></>}
      {loggedIn && <><Link to="/dashboard" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Dashboard</Link><Link to="/connections" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Platform Accounts</Link><Link to="/create-work" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Create Work</Link><Link to="/create-website" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Create Website</Link><Link to="/my-created-work" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>My Created Work</Link><Link to="/referrals" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Refer & Earn</Link><Link to="/wallet" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Wallet</Link><Link to="/transactions" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Transactions</Link><Link to="/exchange" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Exchange</Link><Link to="/notifications" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Notifications</Link><Link to="/account" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Account</Link><Link to="/domain-management" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>My Domains</Link><Link to="/my-active-work" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>My Active Works</Link><Link to="/my-submission" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>My Submission</Link><Link to="/work-review" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Work Review</Link><Link to="/my-blog" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>My Blog</Link>
        {loggedIn && <Link to="/ads" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px', fontWeight: location.pathname === '/ads' ? 700 : 400 }}>Ads Network</Link>}{isAdmin && <><Link to="/admin" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px', fontWeight: 700 }}>Admin</Link><Link to="/admin/analytics" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Analytics</Link><Link to="/admin/payment-accounts" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Payment Accounts</Link><Link to="/admin/database" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Database</Link><Link to="/admin/task-rates" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Task Rates</Link><Link to="/admin/referrals" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Referral Rewards</Link><Link to="/admin/infrastructure" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Infrastructure</Link><Link to="/admin/profile-videos" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Profile Videos</Link></>}
        <button onClick={handleLogout} style={{ color: 'white', background: 'transparent', border: '1px solid rgba(255,255,255,0.5)', borderRadius: 6, padding: '5px 12px', cursor: 'pointer' }}>Logout</button></>}
    </div>
  </nav>
}

const SUBDOMAIN_ROUTES = { 'billing.shopnoltd.dpdns.org': '/billing', 'payment.shopnoltd.dpdns.org': '/payments', 'exchange.shopnoltd.dpdns.org': '/exchange', 'admin.shopnoltd.dpdns.org': '/admin', 'support.shopnoltd.dpdns.org': '/dashboard' }
function SubdomainRedirect() { const navigate = useNavigate(); const location = useLocation(); useEffect(() => { const target = SUBDOMAIN_ROUTES[window.location.hostname]; if (target && location.pathname === '/') navigate(target, { replace: true }) }, []); return null }

function OAuthProviderCallback() {
  useEffect(() => {
    window.location.replace(`/api/v1/omnichannel/oauth/callback${window.location.search}`)
  }, [])
  return <main style={{ maxWidth: 720, margin: '80px auto', padding: 24, textAlign: 'center' }}>
    <h1>Finishing provider connection…</h1>
    <p>Please wait while Shopnoltd securely completes the authorization.</p>
  </main>
}

const ADSENSE_CLIENT = 'ca-pub-4532970890139771'

const PUBLIC_AD_ROUTES = [
  /^\/about$/,
  /^\/contact$/,
  /^\/terms$/,
  /^\/$/,
  /^\/pricing$/,
  /^\/profiles$/,
  /^\/profile\/interior-business$/,
  /^\/profile\/data-management$/,
  /^\/blog$/,
  /^\/blog\/[^/]+$/,
  /^\/services$/,
  /^\/downloads$/,
  /^\/phone$/,
  /^\/domain-registration$/,
  /^\/privacy$/,
  /^\/plugins$/,
]

function shouldLoadAdSense(pathname) {
  return PUBLIC_AD_ROUTES.some((pattern) => pattern.test(pathname))
}

function AdSenseLoader() {
  const location = useLocation()
  useEffect(() => {
    if (!shouldLoadAdSense(location.pathname)) return
    if (document.querySelector('script[data-shopnoltd-adsense="true"]')) return
    const script = document.createElement('script')
    script.async = true
    script.crossOrigin = 'anonymous'
    script.dataset.shopnoltdAdsense = 'true'
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT}`
    document.head.appendChild(script)
    return () => {}
  }, [location.pathname])
  return null
}

function AnalyticsTracker() {
  const location = useLocation()
  useEffect(() => { trackPageView(location.pathname + location.search) }, [location.pathname, location.search])
  return null
}

function App() {
  return <BrowserRouter><AnalyticsTracker /><AdSenseLoader /><Nav /><SubdomainRedirect /><Routes>
    <Route path="/" element={<Home />} /><Route path="/pricing" element={<Pricing />} /><Route path="/privacy" element={<Privacy />} /><Route path="/about" element={<About />} /><Route path="/contact" element={<Contact />} /><Route path="/terms" element={<Terms />} /><Route path="/create-website" element={<ProtectedRoute><WebsiteBuilder /></ProtectedRoute>} /><Route path="/discover" element={<ProtectedRoute><Discover /></ProtectedRoute>} /><Route path="/feed" element={<ProtectedRoute><SocialFeed /></ProtectedRoute>} /><Route path="/post/:id" element={<ProtectedRoute><PostDetail /></ProtectedRoute>} />
    <Route path="/work" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} /><Route path="/referrals" element={<ProtectedRoute><ReferralHub /></ProtectedRoute>} /><Route path="/work/:id" element={<ProtectedRoute><WorkDetail /></ProtectedRoute>} /><Route path="/create-work" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} /><Route path="/my-created-work" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} /><Route path="/my-active-work" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} /><Route path="/my-submission" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} /><Route path="/work-review" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} />
    <Route path="/account" element={<ProtectedRoute><AccountHub /></ProtectedRoute>} /><Route path="/notifications" element={<ProtectedRoute><AccountHub /></ProtectedRoute>} />
    <Route path="/profiles" element={<Profiles />} /><Route path="/profile/data-management" element={<DataManagementProfile />} /><Route path="/profile/interior-business" element={<InteriorBusinessProfile />} />
    <Route path="/blog" element={<Blog />} /><Route path="/ads" element={<ProtectedRoute><AdNetwork /></ProtectedRoute>} /><Route path="/affiliate" element={<Affiliate />} /><Route path="/blog/:slug" element={<BlogPost />} /><Route path="/plugins" element={<Plugins />} /><Route path="/services" element={<Services />} /><Route path="/vpn" element={<ProtectedRoute><VPN /></ProtectedRoute>} /><Route path="/downloads" element={<Downloads />} /><Route path="/phone" element={<Phone />} /><Route path="/domain-registration" element={<DomainRegistration />} />
    <Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} /><Route path="/callback" element={<Callback />} /><Route path="/connections/oauth/callback" element={<OAuthProviderCallback />} /><Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} /><Route path="/connections" element={<ProtectedRoute><OmnichannelConnections /></ProtectedRoute>} /><Route path="/ai" element={<ProtectedRoute><AIWorkspace /></ProtectedRoute>} /><Route path="/ai/connections" element={<ProtectedRoute><AIConnections /></ProtectedRoute>} /><Route path="/my-blog" element={<ProtectedRoute><MyBlog /></ProtectedRoute>} /><Route path="/domain-management" element={<ProtectedRoute><DomainManagement /></ProtectedRoute>} />
    <Route path="/billing" element={<ProtectedRoute><FinancialCenter view="billing" /></ProtectedRoute>} /><Route path="/subscriptions" element={<ProtectedRoute><FinancialCenter view="subscriptions" /></ProtectedRoute>} /><Route path="/invoices" element={<ProtectedRoute><FinancialCenter view="invoices" /></ProtectedRoute>} /><Route path="/checkout" element={<ProtectedRoute><CheckoutCurrencySafe /></ProtectedRoute>} /><Route path="/checkout/complete" element={<ProtectedRoute><CheckoutComplete /></ProtectedRoute>} /><Route path="/payments" element={<ProtectedRoute><FinancialCenter view="payments" /></ProtectedRoute>} /><Route path="/transactions" element={<ProtectedRoute><FinancialCenter view="transactions" /></ProtectedRoute>} /><Route path="/wallet" element={<ProtectedRoute><FinancialCenter view="wallet" /></ProtectedRoute>} /><Route path="/wallet/ledger" element={<ProtectedRoute><FinancialCenter view="ledger" /></ProtectedRoute>} /><Route path="/exchange" element={<ProtectedRoute><FinancialCenter view="exchange" /></ProtectedRoute>} /><Route path="/reports" element={<ProtectedRoute><FinancialCenter view="reports" /></ProtectedRoute>} />
    <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} /><Route path="/admin/analytics" element={<AdminRoute><AdminAnalytics /></AdminRoute>} /><Route path="/admin/payment-accounts" element={<AdminRoute><PaymentAccountsAdmin /></AdminRoute>} /><Route path="/admin/database" element={<AdminRoute><DatabaseControlPlane /></AdminRoute>} /><Route path="/admin/task-rates" element={<AdminRoute><TaskRatesAdmin /></AdminRoute>} /><Route path="/admin/referrals" element={<AdminRoute><ReferralAdmin /></AdminRoute>} /><Route path="/admin/blog" element={<AdminRoute><BlogAdmin /></AdminRoute>} /><Route path="/admin/infrastructure" element={<AdminRoute><AdminInfrastructure /></AdminRoute>} /><Route path="/admin/profile-videos" element={<AdminRoute><AdminProfileVideos /></AdminRoute>} /><Route path="/admin/ai-models" element={<AdminRoute><AIModels /></AdminRoute>} />
  </Routes></BrowserRouter>
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
import { scheduleTokenRefresh } from './lib/tokenRefresh'
scheduleTokenRefresh()
