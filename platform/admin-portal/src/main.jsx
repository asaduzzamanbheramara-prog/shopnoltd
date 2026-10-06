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
import ThreeDDashboard from './pages/ThreeDDashboard'
import DatabaseManagement from './pages/DatabaseManagement'
import Login from './pages/Login'
import Callback from './pages/Callback'
import AdminRoute from './components/AdminRoute'

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
          <li><Link to="/3d" style={{ color: 'white' }}>3D Insights</Link></li>
          <li><Link to="/database" style={{ color: 'white' }}>Database Management</Link></li>
          <li><a href="https://shopnoltd.dpdns.org/admin/database" style={{ color: 'white' }}>Shopnoltd DB Control Plane</a></li>
        </ul>
      </nav>
      <main style={{ flex: 1, padding: 32, background: '#f1f5f9' }}>{children}</main>
    </div>
  )
}

function AdminRoutes() {
  return <Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/users" element={<Users />} />
    <Route path="/tenants" element={<Tenants />} />
    <Route path="/payments" element={<Payments />} />
    <Route path="/plans" element={<Plans />} />
    <Route path="/streams" element={<Streams />} />
    <Route path="/releases" element={<AppReleases />} />
    <Route path="/3d" element={<ThreeDDashboard />} />
    <Route path="/database" element={<DatabaseManagement />} />
  </Routes>
}

function Forbidden() {
  return <main style={{ maxWidth: 640, margin: '80px auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
    <h1>Shopnoltd Admin Access Denied</h1>
    <p>Your Shopnoltd account is authenticated but is not authorized for the admin portal.</p>
    <a href="https://shopnoltd.dpdns.org/dashboard">Return to Shopnoltd</a>
  </main>
}

function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/callback" element={<Callback />} />
          <Route path="/forbidden" element={<Forbidden />} />
          <Route path="*" element={<AdminRoute><Layout><AdminRoutes /></Layout></AdminRoute>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
