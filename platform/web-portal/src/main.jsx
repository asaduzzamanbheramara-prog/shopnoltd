import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Pricing from './pages/Pricing'
import Login from './pages/Login'
import Register from './pages/Register'
import Callback from './pages/Callback'
import Dashboard from './pages/Dashboard'
import Blog from './pages/Blog'
import Plugins from './pages/Plugins'
function Nav() {
  return (
    <nav style={{ display: 'flex', alignItems: 'center', gap: 24, padding: 16, background: '#0ea5e9', color: 'white' }}>
      <Link to="/" style={{ color: 'white', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 20, textDecoration: 'none' }}>
        <img src="/logo.svg" alt="Shopnoltd" style={{ height: 28 }} />
        Shopnoltd
      </Link>
      <Link to="/pricing" style={{ color: 'white' }}>Pricing</Link>
      <Link to="/blog" style={{ color: 'white' }}>Blog</Link>
      <Link to="/plugins" style={{ color: 'white' }}>Plugins</Link>
      <Link to="/login" style={{ color: 'white' }}>Login</Link>
      <Link to="/register" style={{ color: 'white' }}>Register</Link>
      <Link to="/dashboard" style={{ color: 'white' }}>Dashboard</Link>
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
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/callback" element={<Callback />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  )
}
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
