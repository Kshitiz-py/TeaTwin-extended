import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    watch: { usePolling: true },
    proxy: {
      '/api/agent': {
        target: 'http://ai-agent:8003',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://cmsd-twin-service:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://cmsd-twin-service:8000',
        ws: true,
      },
    },
  },
});