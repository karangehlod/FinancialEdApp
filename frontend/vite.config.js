import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Bundle analyzer — only active when ANALYZE=true
// Run with: ANALYZE=true npm run build
const visualizer = process.env.ANALYZE
  ? (await import('rollup-plugin-visualizer')).visualizer
  : null

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/__tests__/**',
        'src/main.tsx',
        'src/vite-env.d.ts',
      ],
    },
  },
  plugins: [
    react(),
    ...(visualizer
      ? [visualizer({ open: true, gzipSize: true, brotliSize: true, filename: 'dist/stats.html' })]
      : []),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@features': path.resolve(__dirname, './src/features'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@services': path.resolve(__dirname, './src/services'),
      '@store': path.resolve(__dirname, './src/store'),
      '@types': path.resolve(__dirname, './src/types'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@lib': path.resolve(__dirname, './src/lib'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // Forward all /api requests to backend as-is (no path rewrite).
      // This preserves the full /api/v1/... path the backend expects.
      // CORS errors are avoided because the request appears same-origin.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // No rewrite — backend expects /api/v1/... paths
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: process.env.NODE_ENV !== 'production',  // No sourcemaps in prod for security
    // Use Vite's built-in esbuild minifier so CI does not require the optional terser package.
    minify: 'esbuild',
    // Code splitting configuration for better bundle optimization
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate vendor chunks
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-ui': ['framer-motion', 'lucide-react', 'react-hot-toast'],
          // P2-10: Only keep recharts (remove chart.js duplication)
          'vendor-charts': ['recharts'],
          'vendor-utils': ['axios', 'zustand', 'date-fns'],
          'vendor-query': ['@tanstack/react-query'],  // P2-10: React Query

          // Separate page chunks — point to migrated .tsx files
          'page-auth': [
            './src/pages/LoginPage.tsx',
            './src/pages/RegisterPage.tsx',
          ],
          'page-dashboard': ['./src/pages/DashboardPage.tsx'],
          'page-financial': [
            './src/pages/ExpensesPage.tsx',
            './src/pages/BudgetsPage.tsx',
            './src/pages/GoalsPage.tsx',
            './src/pages/LoansPage.tsx',
          ],
          'page-reports': ['./src/pages/ReportsPage.tsx'],
          'page-settings': ['./src/pages/SettingsPage.tsx'],
          'page-chat': ['./src/pages/ChatPage.tsx'],

          // Shared components
          'shared-components': ['./src/components/Layout.tsx'],
        },
      },
    },
    // Increase chunk size warning limit since we're optimizing with manual chunks
    chunkSizeWarningLimit: 600,
    // Enable CSS code splitting
    cssCodeSplit: true,
    // Target modern browsers for smaller output
    target: 'es2020',
  },
  // Optimize dependencies
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'zustand',
      'axios',
      'framer-motion',
      'lucide-react',
      'react-hot-toast',
      '@tanstack/react-query',  // P2-10
    ],
    // P2-10: Exclude chart.js (we're consolidating to recharts only)
    exclude: ['chart.js', 'react-chartjs-2'],
  },
})
