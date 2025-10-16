import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '4fcbfe24d1ed.ngrok-free.app' // 👈 add your ngrok frontend host here
    ],
    proxy: {
      // Forward /catalog requests to FastAPI backend
      '/catalog': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/target': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})