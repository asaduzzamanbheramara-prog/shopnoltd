import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

// Real data: cluster health (api-service /cluster) and tenants (oauth-service
// /tenants) are actually fetched and rendered. The schema graph at the
// bottom is a static illustration of oauth-service's current tables
// (Tenant/Customer/UserMirror/Role) -- there's no live schema-introspection
// endpoint yet, so this is drawn from the model definitions by hand, not
// pulled from a database. Extending it to introspect every service's schema
// automatically is future work (see docs/3D_DASHBOARD.md).

function useThreeScene(mountRef, build) {
  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return
    const width = mount.clientWidth, height = 360
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0f172a')
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000)
    camera.position.set(0, 6, 16)
    camera.lookAt(0, 0, 0)
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    mount.appendChild(renderer.domElement)

    scene.add(new THREE.AmbientLight(0xffffff, 0.6))
    const dir = new THREE.DirectionalLight(0xffffff, 0.8)
    dir.position.set(5, 10, 7)
    scene.add(dir)

    const group = new THREE.Group()
    scene.add(group)
    build(group, THREE)

    let dragging = false, lastX = 0
    const onDown = e => { dragging = true; lastX = e.clientX }
    const onUp = () => { dragging = false }
    const onMove = e => {
      if (!dragging) return
      group.rotation.y += (e.clientX - lastX) * 0.01
      lastX = e.clientX
    }
    renderer.domElement.addEventListener('pointerdown', onDown)
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointermove', onMove)

    let raf
    const animate = () => {
      if (!dragging) group.rotation.y += 0.003
      renderer.render(scene, camera)
      raf = requestAnimationFrame(animate)
    }
    animate()

    return () => {
      cancelAnimationFrame(raf)
      renderer.domElement.removeEventListener('pointerdown', onDown)
      window.removeEventListener('pointerup', onUp)
      window.removeEventListener('pointermove', onMove)
      mount.removeChild(renderer.domElement)
      renderer.dispose()
    }
  }, [mountRef, build])
}

function BarChart({ title, data, colorFor }) {
  const mountRef = useRef(null)
  const build = (group) => {
    const n = Math.max(data.length, 1)
    const spacing = 2.2
    data.forEach((d, i) => {
      const height = Math.max(d.value, 0.2)
      const geo = new THREE.BoxGeometry(1.2, height, 1.2)
      const mat = new THREE.MeshStandardMaterial({ color: colorFor(d) })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.position.set((i - (n - 1) / 2) * spacing, height / 2, 0)
      group.add(mesh)
    })
  }
  useThreeScene(mountRef, build)
  return (
    <div style={{ background: 'white', borderRadius: 12, padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      <div ref={mountRef} style={{ width: '100%', height: 360, borderRadius: 8, overflow: 'hidden' }} />
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 8 }}>
        {data.map(d => (
          <span key={d.label} style={{ fontSize: 13, color: '#475569' }}>
            <span style={{ display: 'inline-block', width: 10, height: 10, background: colorFor(d), marginRight: 6, borderRadius: 2 }} />
            {d.label}: {d.value}
          </span>
        ))}
      </div>
      <p style={{ fontSize: 12, color: '#94a3b8', marginBottom: 0 }}>Drag to rotate.</p>
    </div>
  )
}

const SCHEMA = {
  nodes: [
    { id: 'Tenant', pos: [0, 3, 0] },
    { id: 'Customer', pos: [-4, 0, 2] },
    { id: 'UserMirror', pos: [4, 0, 2] },
    { id: 'Role', pos: [0, -3, -3] },
  ],
  edges: [['Tenant', 'Customer'], ['Tenant', 'UserMirror'], ['UserMirror', 'Role']],
}

function SchemaGraph() {
  const mountRef = useRef(null)
  const build = (group) => {
    const positions = {}
    SCHEMA.nodes.forEach(n => {
      positions[n.id] = new THREE.Vector3(...n.pos)
      const geo = new THREE.SphereGeometry(0.7, 24, 24)
      const mat = new THREE.MeshStandardMaterial({ color: '#38bdf8' })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.position.copy(positions[n.id])
      group.add(mesh)

      const canvas = document.createElement('canvas')
      canvas.width = 256; canvas.height = 64
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = 'white'; ctx.font = 'bold 32px sans-serif'; ctx.fillText(n.id, 10, 42)
      const tex = new THREE.CanvasTexture(canvas)
      const label = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }))
      label.scale.set(2.5, 0.6, 1)
      label.position.copy(positions[n.id]).add(new THREE.Vector3(0, 1, 0))
      group.add(label)
    })
    SCHEMA.edges.forEach(([a, b]) => {
      const geo = new THREE.BufferGeometry().setFromPoints([positions[a], positions[b]])
      const mat = new THREE.LineBasicMaterial({ color: '#64748b' })
      group.add(new THREE.Line(geo, mat))
    })
  }
  useThreeScene(mountRef, build)
  return (
    <div style={{ background: 'white', borderRadius: 12, padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
      <h3 style={{ marginTop: 0 }}>Schema Relationships (oauth-service)</h3>
      <div ref={mountRef} style={{ width: '100%', height: 360, borderRadius: 8, overflow: 'hidden' }} />
      <p style={{ fontSize: 12, color: '#94a3b8', marginBottom: 0 }}>
        Static, hand-drawn from the model definitions -- not live schema
        introspection yet. Drag to rotate.
      </p>
    </div>
  )
}

export default function ThreeDDashboard() {
  const { data: cluster } = useQuery({
    queryKey: ['cluster3d'],
    queryFn: () => api.get('/cluster').then(r => r.data),
    retry: false,
  })
  const { data: tenants } = useQuery({
    queryKey: ['tenants3d'],
    queryFn: () => api.get('/tenants').then(r => r.data),
    retry: false,
  })

  const clusterData = cluster
    ? Object.entries(cluster.services || {}).map(([label, status]) => ({ label, value: status === 'ok' ? 1 : 0.3, status }))
    : []
  const planCounts = {}
  ;(tenants || []).forEach(t => { planCounts[t.plan] = (planCounts[t.plan] || 0) + 1 })
  const tenantData = Object.entries(planCounts).map(([label, value]) => ({ label, value }))

  return (
    <div>
      <h1>3D Insights</h1>
      <p style={{ color: '#64748b' }}>
        Live where data exists, clearly marked where it doesn't yet.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 20 }}>
        <BarChart
          title="Service Health"
          data={clusterData.length ? clusterData : [{ label: 'no data yet', value: 0.2, status: 'unknown' }]}
          colorFor={d => (d.status === 'ok' ? '#10b981' : '#ef4444')}
        />
        <BarChart
          title="Tenants by Plan"
          data={tenantData.length ? tenantData : [{ label: 'no data yet', value: 0.2 }]}
          colorFor={() => '#38bdf8'}
        />
        <SchemaGraph />
      </div>
    </div>
  )
}
