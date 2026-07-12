import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import Tenants from './pages/Tenants'
import Payments from './pages/Payments'
import Plans from './pages/Plans'
import Streams from './pages/Streams'
import AppReleases from './pages/AppReleases'
const qc = new QueryClient()
function Layout({ children }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      <nav style={{ width: 220, background: '#0f172a', color: 'white', padding: 20 }}>
        <h2 style={{ color: '#38bdf8' }}>Shopnoltd</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li><Link to="/" style={{ color: 'white' }}>Dashboard</Link></li>
          <li><Link to="/users" style={{ color: 'white' }}>Users</Link></li>
          <li><Link to="/tenants" style={{ color: 'white' }}>Tenants</Link></li>
          <li><Link to="/payments" style={{ color: 'white' }}>Payments</Link></li>
          <li><Link to="/plans" style={{ color: 'white' }}>Plans</Link></li>
          <li><Link to="/streams" style={{ color: 'white' }}>Live Streams</Link></li>
          <li><Link to="/releases" style={{ color: 'white' }}>App Releases</Link></li>
        </ul>
      </nav>
      <main style={{ flex: 1, padding: 32, background: '#f1f5f9' }}>{children}</main>
    </div>
  )
}
function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/users" element={<Users />} />
            <Route path="/tenants" element={<Tenants />} />
            <Route path="/payments" element={<Payments />} />
            <Route path="/plans" element={<Plans />} />
            <Route path="/streams" element={<Streams />} />
            <Route path="/releases" element={<AppReleases />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
