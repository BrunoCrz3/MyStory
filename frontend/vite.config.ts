/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// El backend escucha solo en local (spec1 RNF-12). El proxy evita pedirle CORS.
const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    // Puerto fijo: es el valor de STORYMAKER_LECTURA_URL del backend.
    strictPort: true,
    proxy: {
      '/api': {
        target: BACKEND,
        changeOrigin: true,
        rewrite: (ruta) => ruta.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/**/*.test.{ts,tsx}'],
    setupFiles: ['tests/apoyo/preparar.ts'],
  },
})
