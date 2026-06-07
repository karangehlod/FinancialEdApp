import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Bundle analyzer — only active when ANALYZE=true
const visualizer = process.env.ANALYZE
  ? (await import('rollup-plugin-visualizer')).visualizer
  : null;

export default defineConfig({
  plugins: [
    react(),
    ...(visualizer ? [visualizer({ open: true, gzipSize: true, brotliSize: true, filename: 'dist/stats.html' })] : []),
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/testSetup.js',
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: process.env.NODE_ENV !== 'production',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.debug', 'console.info'],
      },
    },
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router-dom')) {
              return 'vendor-react';
            }
            if (id.includes('framer-motion') || id.includes('lucide-react') || id.includes('react-hot-toast')) {
              return 'vendor-ui';
            }
            if (id.includes('recharts')) {
              return 'vendor-charts';
            }
            if (id.includes('axios') || id.includes('zustand') || id.includes('date-fns')) {
              return 'vendor-utils';
            }
          }
        },
      },
    },
    chunkSizeWarningLimit: 600,
    cssCodeSplit: true,
    target: 'es2020',
  },
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
      '@tanstack/react-query',
    ],
    exclude: ['chart.js', 'react-chartjs-2'],
  },
});