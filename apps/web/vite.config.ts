import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // Read RESIDENT_DEV_TOKEN from the repo-root .env. It's only used by the dev proxy in this
  // Node process and never bundled into the browser code.
  const env = loadEnv(mode, '../..', 'RESIDENT_')
  return {
    plugins: [tanstackRouter({ target: 'react', autoCodeSplitting: true }), react(), tailwindcss()],
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          headers: env.RESIDENT_DEV_TOKEN
            ? { Authorization: `Bearer ${env.RESIDENT_DEV_TOKEN}` }
            : undefined,
        },
      },
    },
  }
})
