import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Pricing from './pages/Pricing'
import Login from './pages/Login'
import Register from './pages/Register'
import Callback from './pages/Callback'
import Dashboard from './pages/Dashboard'
import ProtectedRoute from './components/ProtectedRoute'
import Blog from './pages/Blog'
import Plugins from './pages/Plugins'
import Services from './pages/Services'
import DomainRegistration from "./pages/DomainRegistration";
import AdminDashboard from './pages/AdminDashboard'
import AdminRoute from './components/AdminRoute'
import FinancialCenter from './pages/FinancialCenter'
import { isPlatformAdmin } from './lib/jwt'


const PUBLIC_LINKS = [
  ['Pricing', '/pricing'],
  ['Blog', '/blog'],
  ['Plugins', '/plugins'],
  ['Services', '/services'],
]

function Nav() {
  const navigate = useNavigate()
  const location = useLocation()
  const token = localStorage.getItem('shopno_token')
  const loggedIn = !!token
  const isAdmin = loggedIn && isPlatformAdmin()

  function handleLogout() {
    localStorage.removeItem('shopno_token')
    navigate('/')
  }

  return (
    <nav
      style={{
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 12,
        padding: '12px clamp(14px, 3vw, 24px)',
        background: '#0ea5e9',
        color: 'white',
        boxSizing: 'border-box',
      }}
    >
      <Link
        to="/"
        style={{
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          fontWeight: 700,
          fontSize: 20,
          textDecoration: 'none',
          whiteSpace: 'nowrap',
          marginRight: 'auto',
        }}
      >
        <img
          src="/logo.svg"
          alt="Shopnoltd"
          style={{
            height: 28,
            width: 28,
            objectFit: 'contain',
            flex: '0 0 auto',
          }}
        />
        Shopnoltd
      </Link>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: '8px 16px',
          minWidth: 0,
        }}
      >
        {PUBLIC_LINKS.map(([label, path]) => (
          <Link
            key={path}
            to={path}
            style={{
              color: 'white',
              textDecoration: 'none',
              padding: '6px 2px',
              whiteSpace: 'nowrap',
            }}
          >
            {label}
          </Link>
        ))}
        {!loggedIn && (
          <>
            <Link key="/login" to="/login" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px', whiteSpace: 'nowrap' }}>Login</Link>
            <Link key="/register" to="/register" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px', whiteSpace: 'nowrap' }}>Register</Link>
          </>
        )}
        {loggedIn && (
          <>
            <Link key="/dashboard" to="/dashboard" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px', whiteSpace: 'nowrap' }}>Dashboard</Link>
            {isAdmin && (
              <Link key="/admin" to="/admin" style={{ color: 'white', textDecoration: 'none', padding: '6px 2px', whiteSpace: 'nowrap', fontWeight: 700 }}>Admin</Link>
            )}
            <button
              key="/logout"
              onClick={handleLogout}
              style={{
                color: 'white',
                background: 'transparent',
                border: '1px solid rgba(255,255,255,0.5)',
                borderRadius: 6,
                padding: '5px 12px',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                fontSize: 14,
              }}
            >
              Logout
            </button>
          </>
        )}
      </div>
    </nav>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/blog" element={<Blog />} />
        <Route path="/plugins" element={<Plugins />} />
        <Route path="/services" element={<Services />} />
        <Route path="/domain-registration" element={<DomainRegistration />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/callback" element={<Callback />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/billing" element={<ProtectedRoute><FinancialCenter view="billing" /></ProtectedRoute>} />
        <Route path="/subscriptions" element={<ProtectedRoute><FinancialCenter view="subscriptions" /></ProtectedRoute>} />
        <Route path="/invoices" element={<ProtectedRoute><FinancialCenter view="invoices" /></ProtectedRoute>} />
        <Route path="/checkout" element={<ProtectedRoute><FinancialCenter view="checkout" /></ProtectedRoute>} />
        <Route path="/payments" element={<ProtectedRoute><FinancialCenter view="payments" /></ProtectedRoute>} />
        <Route path="/transactions" element={<ProtectedRoute><FinancialCenter view="transactions" /></ProtectedRoute>} />
        <Route path="/wallet" element={<ProtectedRoute><FinancialCenter view="wallet" /></ProtectedRoute>} />
        <Route path="/wallet/ledger" element={<ProtectedRoute><FinancialCenter view="ledger" /></ProtectedRoute>} />
        <Route path="/exchange" element={<ProtectedRoute><FinancialCenter view="exchange" /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute><FinancialCenter view="reports" /></ProtectedRoute>} />
        <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
      </Routes>
    </BrowserRouter>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
