import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    // Windows Docker volume 掛載需要 polling 才能偵測檔案變更
    watch: {
      usePolling: true,
      interval: 500,
    },
    proxy: {
      '/api': {
        target: 'http://api:8000',
        changeOrigin: true,
      },
    },
  },
})
