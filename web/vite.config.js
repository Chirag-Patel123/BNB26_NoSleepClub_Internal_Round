import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: /api/* is forwarded unchanged to FastAPI on port 8000.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            return 'vendor'
          }
        }
      }
    }
  }
})