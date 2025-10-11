import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        ws: true,
      },
      '/ws': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    // Optimize bundle size with code splitting
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['react', 'react-dom', 'react-router-dom'],
          'charts': ['recharts'],
          'maps': ['leaflet', 'react-leaflet', 'react-leaflet-cluster'],
          'ui': ['lucide-react', 'clsx', 'tailwind-merge'],
          'query': ['@tanstack/react-query', 'axios'],
        },
      },
    },
    chunkSizeWarningLimit: 600, // Increase warning limit to 600KB
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    css: true,
  },
})
