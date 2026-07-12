import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  server: { host: '0.0.0.0', port: 5173, proxy: { '/api': 'http://api-service.shopno-platform.svc.cluster.local:8080' } },
  build: { outDir: 'dist' }
})
