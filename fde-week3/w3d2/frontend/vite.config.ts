import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The UI calls /api/...; Vite forwards those requests to the FastAPI server.
// Override the target with API_URL=http://host:port npm run dev.
const apiTarget = process.env.API_URL ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
