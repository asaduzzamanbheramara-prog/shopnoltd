import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Pricing from './pages/Pricing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
function Nav() {
  return (
    <nav style={{ display: 'flex', gap: 24, padding: 16, background: '#0ea5e9', color: 'white' }}>
      <Link to="/" style={{ color: 'white', fontWeight: 700, fontSize: 20 }}>Shopnoltd</Link>
      <Link to="/pricing" style={{ color: 'white' }}>Pricing</Link>
      <Link to="/login" style={{ color: 'white' }}>Login</Link>
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
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  )
}
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
