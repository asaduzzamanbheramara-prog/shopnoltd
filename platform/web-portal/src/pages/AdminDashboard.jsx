import { useState, useEffect, useRef } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import * as THREE from 'three';
import { Users, Database, BarChart3, Server, Boxes, Search, RefreshCw, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

const TOKENS = {
  bg: '#0F1419',
  surface: '#161C24',
  surfaceRaised: '#1D2530',
  border: '#2A3341',
  text: '#E6EDF3',
  textMuted: '#7D8A9C',
  copper: '#D4A054',
  healthy: '#3FB950',
  degraded: '#E3B341',
  down: '#F85149',
};

const SERVICES = [
  { name: 'domain-service', status: 'healthy', restarts: 0, latency: 42 },
  { name: 'freedomain-service', status: 'healthy', restarts: 1, latency: 58 },
  { name: 'payment-service', status: 'healthy', restarts: 0, latency: 31 },
  { name: 'billing-engine', status: 'degraded', restarts: 4, latency: 210 },
  { name: 'exchange-service', status: 'healthy', restarts: 2, latency: 47 },
  { name: 'code-server', status: 'healthy', restarts: 0, latency: 19 },
  { name: 'automation', status: 'healthy', restarts: 0, latency: 65 },
  { name: 'keycloak', status: 'healthy', restarts: 0, latency: 88 },
  { name: 'gateway', status: 'down', restarts: 0, latency: 0 },
  { name: 'nextcloud', status: 'down', restarts: 12, latency: 0 },
];

const USERS = [
  { name: 'Rahim Ahmed', email: 'rahim@example.com', role: 'customer', wallet: 1240, status: 'active' },
  { name: 'Fatima Begum', email: 'fatima@example.com', role: 'customer', wallet: 320, status: 'active' },
  { name: 'temp-admin', email: 'temp-admin@shopnoltd.dpdns.org', role: 'admin', wallet: 0, status: 'stale — delete' },
  { name: 'Karim Hossain', email: 'karim@example.com', role: 'customer', wallet: 85, status: 'suspended' },
];

const REVENUE = [
  { day: 'Mon', revenue: 420, domains: 3 },
  { day: 'Tue', revenue: 680, domains: 5 },
  { day: 'Wed', revenue: 390, domains: 2 },
  { day: 'Thu', revenue: 812, domains: 7 },
  { day: 'Fri', revenue: 640, domains: 4 },
  { day: 'Sat', revenue: 310, domains: 1 },
  { day: 'Sun', revenue: 205, domains: 1 },
];

function statusColor(s) {
  return s === 'healthy' ? TOKENS.healthy : s === 'degraded' ? TOKENS.degraded : TOKENS.down;
}

function Pulse({ status, seed = 0 }) {
  const color = statusColor(status);
  const path =
    status === 'down'
      ? 'M0,20 L200,20'
      : status === 'degraded'
      ? `M0,20 L20,20 L28,${8 + (seed % 5)} L36,32 L44,4 L52,20 L200,20`
      : `M0,20 L${30 + seed},20 L${38 + seed},6 L${46 + seed},34 L${54 + seed},20 L200,20`;
  return (
    <svg width="100%" height="40" viewBox="0 0 200 40" preserveAspectRatio="none" style={{ display: 'block' }}>
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {status !== 'down' && (
          <animate attributeName="stroke-dasharray" values="0,400;400,400" dur="2.4s" repeatCount="indefinite" />
        )}
      </path>
    </svg>
  );
}

function StatCard({ label, value, sub }) {
  return (
    <div style={{
      background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 10,
      padding: '18px 20px', flex: 1, minWidth: 160,
    }}>
      <div style={{ fontSize: 12, color: TOKENS.textMuted, textTransform: 'uppercase', letterSpacing: 0.6 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 600, color: TOKENS.text, fontFamily: 'IBM Plex Mono, monospace', marginTop: 4 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: TOKENS.textMuted, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function StatusBadge({ status }) {
  const Icon = status === 'healthy' ? CheckCircle2 : status === 'degraded' ? AlertTriangle : XCircle;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: statusColor(status), fontSize: 12, fontFamily: 'IBM Plex Mono, monospace' }}>
      <Icon size={13} /> {status}
    </span>
  );
}

function Topology3D() {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    const width = mount.clientWidth;
    const height = 320;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.set(0, 2, 13);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambient);
    const point = new THREE.PointLight(0xd4a054, 1.2);
    point.position.set(5, 8, 8);
    scene.add(point);

    const nodes = [];
    const radius = 5;
    SERVICES.forEach((svc, i) => {
      const angle = (i / SERVICES.length) * Math.PI * 2;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = (i % 3 - 1) * 1.2;

      const color = new THREE.Color(statusColor(svc.status));
      const geo = new THREE.SphereGeometry(svc.status === 'down' ? 0.25 : 0.35, 24, 24);
      const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.35, roughness: 0.4 });
      const sphere = new THREE.Mesh(geo, mat);
      sphere.position.set(x, y, z);
      group.add(sphere);
      nodes.push({ x, y, z });

      const lineMat = new THREE.LineBasicMaterial({ color: 0x2a3341, transparent: true, opacity: 0.5 });
      const points = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(x, y, z)];
      const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
      group.add(new THREE.Line(lineGeo, lineMat));
    });

    const coreGeo = new THREE.SphereGeometry(0.5, 24, 24);
    const coreMat = new THREE.MeshStandardMaterial({ color: 0xd4a054, emissive: 0xd4a054, emissiveIntensity: 0.5 });
    group.add(new THREE.Mesh(coreGeo, coreMat));

    let frameId;
    const animate = () => {
      group.rotation.y += 0.0025;
      renderer.render(scene, camera);
      frameId = requestAnimationFrame(animate);
    };
    animate();

    const handleResize = () => {
      const w = mount.clientWidth;
      camera.aspect = w / height;
      camera.updateProjectionMatrix();
      renderer.setSize(w, height);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', handleResize);
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  return <div ref={mountRef} style={{ width: '100%', height: 320, borderRadius: 10, overflow: 'hidden' }} />;
}

export default function AdminDashboard() {
  const [tab, setTab] = useState('services');
  const [query, setQuery] = useState('');

  const navItems = [
    { id: 'services', label: 'Services', icon: Server },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'database', label: 'Database', icon: Database },
    { id: 'reports', label: 'Reports', icon: BarChart3 },
    { id: 'topology', label: '3D Topology', icon: Boxes },
  ];

  return (
    <div style={{
      fontFamily: 'IBM Plex Sans, system-ui, sans-serif', background: TOKENS.bg, color: TOKENS.text,
      minHeight: 600, display: 'flex', borderRadius: 12, overflow: 'hidden', border: `1px solid ${TOKENS.border}`,
    }}>
      {/* Sidebar */}
      <div style={{ width: 190, background: TOKENS.surface, borderRight: `1px solid ${TOKENS.border}`, padding: '20px 12px', flexShrink: 0 }}>
        <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 14, fontWeight: 600, color: TOKENS.copper, padding: '0 10px 20px' }}>
          shopnoltd<span style={{ color: TOKENS.textMuted }}>/admin</span>
        </div>
        {navItems.map(({ id, label, icon: Icon }) => (
          <div key={id} onClick={() => setTab(id)} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px', borderRadius: 7, cursor: 'pointer',
            marginBottom: 2, fontSize: 13.5,
            background: tab === id ? TOKENS.surfaceRaised : 'transparent',
            color: tab === id ? TOKENS.text : TOKENS.textMuted,
          }}>
            <Icon size={15} /> {label}
          </div>
        ))}
      </div>

      {/* Main */}
      <div style={{ flex: 1, padding: 24, overflow: 'auto' }}>
        {/* Pulse strip — always visible */}
        <div style={{ display: 'flex', gap: 14, overflowX: 'auto', paddingBottom: 16, marginBottom: 20, borderBottom: `1px solid ${TOKENS.border}` }}>
          {SERVICES.map((svc, i) => (
            <div key={svc.name} style={{ minWidth: 130 }}>
              <div style={{ fontSize: 10.5, color: TOKENS.textMuted, fontFamily: 'IBM Plex Mono, monospace', marginBottom: 2 }}>{svc.name}</div>
              <Pulse status={svc.status} seed={i * 7} />
            </div>
          ))}
        </div>

        {tab === 'services' && (
          <>
            <div style={{ display: 'flex', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}>
              <StatCard label="Services Healthy" value={`${SERVICES.filter(s => s.status === 'healthy').length}/${SERVICES.length}`} />
              <StatCard label="Restarts (24h)" value={SERVICES.reduce((a, s) => a + s.restarts, 0)} />
              <StatCard label="Avg Latency" value="52ms" />
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: TOKENS.textMuted, fontSize: 11, textTransform: 'uppercase' }}>
                  <th style={{ padding: '8px 10px' }}>Service</th>
                  <th style={{ padding: '8px 10px' }}>Status</th>
                  <th style={{ padding: '8px 10px' }}>Restarts</th>
                  <th style={{ padding: '8px 10px' }}>Latency</th>
                </tr>
              </thead>
              <tbody>
                {SERVICES.map(svc => (
                  <tr key={svc.name} style={{ borderTop: `1px solid ${TOKENS.border}` }}>
                    <td style={{ padding: '10px', fontFamily: 'IBM Plex Mono, monospace' }}>{svc.name}</td>
                    <td style={{ padding: '10px' }}><StatusBadge status={svc.status} /></td>
                    <td style={{ padding: '10px', color: TOKENS.textMuted }}>{svc.restarts}</td>
                    <td style={{ padding: '10px', color: TOKENS.textMuted }}>{svc.latency > 0 ? `${svc.latency}ms` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {tab === 'users' && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 8, padding: '8px 12px' }}>
              <Search size={14} color={TOKENS.textMuted} />
              <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search users by name or email"
                style={{ background: 'transparent', border: 'none', outline: 'none', color: TOKENS.text, fontSize: 13, width: '100%' }} />
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: TOKENS.textMuted, fontSize: 11, textTransform: 'uppercase' }}>
                  <th style={{ padding: '8px 10px' }}>Name</th>
                  <th style={{ padding: '8px 10px' }}>Role</th>
                  <th style={{ padding: '8px 10px' }}>Wallet</th>
                  <th style={{ padding: '8px 10px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {USERS.filter(u => u.name.toLowerCase().includes(query.toLowerCase()) || u.email.toLowerCase().includes(query.toLowerCase())).map(u => (
                  <tr key={u.email} style={{ borderTop: `1px solid ${TOKENS.border}` }}>
                    <td style={{ padding: '10px' }}>{u.name}<div style={{ fontSize: 11, color: TOKENS.textMuted }}>{u.email}</div></td>
                    <td style={{ padding: '10px', color: TOKENS.textMuted }}>{u.role}</td>
                    <td style={{ padding: '10px', fontFamily: 'IBM Plex Mono, monospace' }}>৳{u.wallet}</td>
                    <td style={{ padding: '10px', color: u.status.includes('stale') ? TOKENS.down : u.status === 'suspended' ? TOKENS.degraded : TOKENS.healthy }}>{u.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {tab === 'database' && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ textAlign: 'left', color: TOKENS.textMuted, fontSize: 11, textTransform: 'uppercase' }}>
                <th style={{ padding: '8px 10px' }}>Service DB</th>
                <th style={{ padding: '8px 10px' }}>Migration Rev</th>
                <th style={{ padding: '8px 10px' }}>Last Backup</th>
                <th style={{ padding: '8px 10px' }}></th>
              </tr>
            </thead>
            <tbody>
              {[
                { db: 'domain-service', rev: '702e06d (current)', backup: '3h ago' },
                { db: 'freedomain-service', rev: '8c76d05 (current)', backup: '3h ago' },
                { db: 'payment-service', rev: 'pending Alembic migration', backup: '11h ago' },
                { db: 'keycloak', rev: 'n/a', backup: '1d ago' },
              ].map(r => (
                <tr key={r.db} style={{ borderTop: `1px solid ${TOKENS.border}` }}>
                  <td style={{ padding: '10px', fontFamily: 'IBM Plex Mono, monospace' }}>{r.db}</td>
                  <td style={{ padding: '10px', color: TOKENS.textMuted }}>{r.rev}</td>
                  <td style={{ padding: '10px', color: TOKENS.textMuted }}>{r.backup}</td>
                  <td style={{ padding: '10px' }}>
                    <button style={{ background: TOKENS.surfaceRaised, border: `1px solid ${TOKENS.border}`, color: TOKENS.copper, borderRadius: 6, padding: '5px 10px', fontSize: 12, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      <RefreshCw size={12} /> Trigger backup
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === 'reports' && (
          <>
            <div style={{ display: 'flex', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}>
              <StatCard label="Revenue (7d)" value="৳3,457" sub="+12% vs last week" />
              <StatCard label="Domains Registered" value="23" sub="this week" />
              <StatCard label="Active Wallets" value="184" />
            </div>
            <div style={{ background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 10, padding: 16, marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: TOKENS.textMuted, marginBottom: 8 }}>REVENUE — LAST 7 DAYS</div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={REVENUE}>
                  <defs>
                    <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={TOKENS.copper} stopOpacity={0.4} />
                      <stop offset="100%" stopColor={TOKENS.copper} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={TOKENS.border} vertical={false} />
                  <XAxis dataKey="day" stroke={TOKENS.textMuted} fontSize={11} />
                  <YAxis stroke={TOKENS.textMuted} fontSize={11} />
                  <Tooltip contentStyle={{ background: TOKENS.surfaceRaised, border: `1px solid ${TOKENS.border}`, borderRadius: 6, fontSize: 12 }} />
                  <Area type="monotone" dataKey="revenue" stroke={TOKENS.copper} fill="url(#rev)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div style={{ background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 12, color: TOKENS.textMuted, marginBottom: 8 }}>DOMAINS REGISTERED — LAST 7 DAYS</div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={REVENUE}>
                  <CartesianGrid stroke={TOKENS.border} vertical={false} />
                  <XAxis dataKey="day" stroke={TOKENS.textMuted} fontSize={11} />
                  <YAxis stroke={TOKENS.textMuted} fontSize={11} />
                  <Tooltip contentStyle={{ background: TOKENS.surfaceRaised, border: `1px solid ${TOKENS.border}`, borderRadius: 6, fontSize: 12 }} />
                  <Bar dataKey="domains" fill={TOKENS.healthy} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}

        {tab === 'topology' && (
          <>
            <div style={{ fontSize: 12, color: TOKENS.textMuted, marginBottom: 8 }}>
              CLUSTER TOPOLOGY — copper core is the ingress; sphere color = health status
            </div>
            <Topology3D />
          </>
        )}
      </div>
    </div>
  );
}
