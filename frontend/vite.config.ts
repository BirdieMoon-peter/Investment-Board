import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // The framework caches independently without hoisting lazy-screen UI code.
        manualChunks(id) {
          if (!id.includes('/node_modules/')) return
          if (/\/(?:react|react-dom|scheduler)\//.test(id)) return 'react-vendor'
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
  },
})
