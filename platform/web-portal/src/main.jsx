import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
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

const NAV_LINKS = [
  ['Pricing', '/pricing'],
  ['Blog', '/blog'],
  ['Plugins', '/plugins'],
  ['Services', '/services'],
  ['Login', '/login'],
  ['Register', '/register'],
  ['Dashboard', '/dashboard'],
]

function Nav() {
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
        {NAV_LINKS.map(([label, path]) => (
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
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/callback" element={<Callback />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
