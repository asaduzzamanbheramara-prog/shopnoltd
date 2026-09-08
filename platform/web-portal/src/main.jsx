import React, { useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Pricing from './pages/Pricing'
import Login from './pages/Login'
import Register from './pages/Register'
import Callback from './pages/Callback'
import Dashboard from './pages/Dashboard'
import AIWorkspace from './pages/AIWorkspace'
import ProtectedRoute from './components/ProtectedRoute'
import Blog from './pages/Blog'
import BlogAdmin from './pages/BlogAdmin'
import MyBlog from './pages/MyBlog'
import BlogPost from './pages/BlogPost'
import Plugins from './pages/Plugins'
import Services from './pages/Services'
import DomainRegistration from "./pages/DomainRegistration";
import AdminDashboard from './pages/AdminDashboard'
import AdminInfrastructure from './pages/AdminInfrastructure'
import DatabaseControlPlane from './pages/DatabaseControlPlaneEnhanced'
import AdminRoute from './components/AdminRoute'
import FinancialCenter from './pages/FinancialCenter'
import SocialFeed from './pages/SocialFeed'
import PostDetail from './pages/PostDetail'
import WorkHub from './pages/WorkHub'
import AccountHub from './pages/AccountHub'
import { isPlatformAdmin } from './lib/jwt'

const PUBLIC_LINKS = [['Pricing', '/pricing'], ['Feed', '/feed'], ['Work', '/work'], ['Blog', '/blog'], ['Services', '/services']]

function Nav() {
  const navigate = useNavigate(); const location = useLocation(); const token = localStorage.getItem('shopno_token'); const loggedIn = !!token; const isAdmin = loggedIn && isPlatformAdmin()
  function handleLogout() { localStorage.removeItem('shopno_token'); localStorage.removeItem('shopno_refresh_token'); navigate('/') }
  return <nav style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 12, padding: '12px clamp(14px, 3vw, 24px)', background: '#0ea5e9', color: 'white', boxSizing: 'border-box' }}>
    <Link to="/" style={{ color: 'white', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 20, textDecoration: 'none', whiteSpace: 'nowrap', marginRight: 'auto' }}><img src="/logo.svg" alt="Shopnoltd" style={{ height: 28, width: 28, objectFit: 'contain' }} />Shopnoltd</Link>
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'flex-end', gap: '8px 16px', minWidth: 0 }}>
      {PUBLIC_LINKS.map(([label, path]) => <Link key={path} to={path} style={{ color: 'white', textDecoration: 'none', padding: '6px 2px', whiteSpace: 'nowrap', fontWeight: location.pathname === path ? 700 : 400 }}>{label}</Link>)}
      {!loggedIn && <><Link to="/login" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Login</Link><Link to="/register" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Register</Link></>}
      {loggedIn && <><Link to="/dashboard" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Dashboard</Link><Link to="/wallet" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Wallet</Link><Link to="/notifications" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Notifications</Link><Link to="/account" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Account</Link><Link to="/my-active-work" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>My Active Works</Link><Link to="/my-submission" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>My Submission</Link><Link to="/work-review" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Work Review</Link><Link to="/my-blog" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>My Blog</Link>
        {isAdmin && <><Link to="/admin" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px', fontWeight: 700 }}>Admin</Link><Link to="/admin/infrastructure" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px' }}>Infrastructure</Link></>}
        <button onClick={handleLogout} style={{ color: 'white', background: 'transparent', border: '1px solid rgba(255,255,255,0.5)', borderRadius: 6, padding: '5px 12px', cursor: 'pointer' }}>Logout</button></>}
    </div>
  </nav>
}

const SUBDOMAIN_ROUTES = { 'billing.shopnoltd.dpdns.org': '/billing', 'payment.shopnoltd.dpdns.org': '/payments', 'exchange.shopnoltd.dpdns.org': '/exchange', 'admin.shopnoltd.dpdns.org': '/admin', 'support.shopnoltd.dpdns.org': '/dashboard' }
function SubdomainRedirect() { const navigate = useNavigate(); const location = useLocation(); useEffect(() => { const target = SUBDOMAIN_ROUTES[window.location.hostname]; if (target && location.pathname === '/') navigate(target, { replace: true }) }, []); return null }

function App() {
  return <BrowserRouter><Nav /><SubdomainRedirect /><Routes>
    <Route path="/" element={<Home />} /><Route path="/pricing" element={<Pricing />} /><Route path="/feed" element={<SocialFeed />} /><Route path="/post/:id" element={<PostDetail />} />
    <Route path="/work" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} /><Route path="/create-work" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} /><Route path="/my-active-work" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} /><Route path="/my-submission" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} /><Route path="/work-review" element={<ProtectedRoute><WorkHub /></ProtectedRoute>} />
    <Route path="/account" element={<ProtectedRoute><AccountHub /></ProtectedRoute>} /><Route path="/notifications" element={<ProtectedRoute><AccountHub /></ProtectedRoute>} />
    <Route path="/blog" element={<Blog />} /><Route path="/blog/:slug" element={<BlogPost />} /><Route path="/plugins" element={<Plugins />} /><Route path="/services" element={<Services />} /><Route path="/domain-registration" element={<DomainRegistration />} />
    <Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} /><Route path="/callback" element={<Callback />} /><Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} /><Route path="/ai" element={<ProtectedRoute><AIWorkspace /></ProtectedRoute>} /><Route path="/my-blog" element={<ProtectedRoute><MyBlog /></ProtectedRoute>} />
    <Route path="/billing" element={<ProtectedRoute><FinancialCenter view="billing" /></ProtectedRoute>} /><Route path="/subscriptions" element={<ProtectedRoute><FinancialCenter view="subscriptions" /></ProtectedRoute>} /><Route path="/invoices" element={<ProtectedRoute><FinancialCenter view="invoices" /></ProtectedRoute>} /><Route path="/checkout" element={<ProtectedRoute><FinancialCenter view="checkout" /></ProtectedRoute>} /><Route path="/payments" element={<ProtectedRoute><FinancialCenter view="payments" /></ProtectedRoute>} /><Route path="/transactions" element={<ProtectedRoute><FinancialCenter view="transactions" /></ProtectedRoute>} /><Route path="/wallet" element={<ProtectedRoute><FinancialCenter view="wallet" /></ProtectedRoute>} /><Route path="/wallet/ledger" element={<ProtectedRoute><FinancialCenter view="ledger" /></ProtectedRoute>} /><Route path="/exchange" element={<ProtectedRoute><FinancialCenter view="exchange" /></ProtectedRoute>} /><Route path="/reports" element={<ProtectedRoute><FinancialCenter view="reports" /></ProtectedRoute>} />
    <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} /><Route path="/admin/database" element={<AdminRoute><DatabaseControlPlane /></AdminRoute>} /><Route path="/admin/blog" element={<AdminRoute><BlogAdmin /></AdminRoute>} /><Route path="/admin/infrastructure" element={<AdminRoute><AdminInfrastructure /></AdminRoute>} />
  </Routes></BrowserRouter>
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
import { scheduleTokenRefresh } from './lib/tokenRefresh'
scheduleTokenRefresh()
