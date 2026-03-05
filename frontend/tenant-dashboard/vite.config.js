import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    // Drop console.log in production builds (keep console.error and console.warn)
    ...(mode === 'production' && {
      esbuild: {
        drop: ['debugger'],
        pure: ['console.log'],
      },
    }),
    // Explicitly define env variables to ensure they're available
    define: {
      'import.meta.env.VITE_API_URL': JSON.stringify(env.VITE_API_URL || 'http://localhost:8000'),
      'import.meta.env.VITE_CLIENT_ID': JSON.stringify(env.VITE_CLIENT_ID || 'example'),
      'import.meta.env.VITE_WEBSITE_BUILDER_URL': JSON.stringify(env.VITE_WEBSITE_BUILDER_URL || 'http://localhost:3000'),
      'import.meta.env.VITE_APP_URL': JSON.stringify(env.VITE_APP_URL || 'http://localhost:5173'),
      'import.meta.env.VITE_INBOUND_EMAIL_DOMAIN': JSON.stringify(env.VITE_INBOUND_EMAIL_DOMAIN || 'holidaytoday.co.za'),
    },
    server: {
      port: 5173,
      // Proxy API requests to backend to avoid CORS issues
      proxy: {
        // Proxy main backend API requests
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        // Proxy website builder requests (avoids CORS in dev)
        // /wb/api/... → http://localhost:3000/api/...
        '/wb': {
          target: env.VITE_WEBSITE_BUILDER_URL || 'http://localhost:3000',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/wb/, ''),
        },
      },
    },
  }
})
