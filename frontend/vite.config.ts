import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// During development the React app runs on :5173 and forwards API calls to the
// FastAPI backend on :8000. In production FastAPI serves the built files itself.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    chunkSizeWarningLimit: 1200,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
