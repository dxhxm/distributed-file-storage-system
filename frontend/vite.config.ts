import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/cluster': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/nodes': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/files': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/upload': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/replicate': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/time': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/sync-time': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/raft': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/leader': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/state': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/node-status': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'es2022',
    outDir: 'dist',
  },
});
