import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: /api/* is forwarded unchanged to FastAPI on port 8000.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
