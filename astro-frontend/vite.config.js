import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'astro-frontend.onrender.com' // 👈 your deployed frontend host
    ],
    proxy: {
      // Forward /catalog requests to FastAPI backend
      '/catalog': {
        target: 'https://astro-app-es0g.onrender.com', // 👈 your deployed backend
        changeOrigin: true,
      },
      '/target': {
        target: 'https://astro-app-es0g.onrender.com', // 👈 your deployed backend
        changeOrigin: true,
      },
    },
  },
})
