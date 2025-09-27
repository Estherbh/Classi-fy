import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@/components": path.resolve(__dirname, "./src/components"),
      "@/utils": path.resolve(__dirname, "./src/utils"),
      "@/services": path.resolve(__dirname, "./src/services"),
      "@/api": path.resolve(__dirname, "./src/api"),
      "@/assets": path.resolve(__dirname, "./src/assets")
    },
  },
  
  // Configuration du serveur de développement
  server: {
    port: 5173,
    host: true,
    cors: true
  },
  
  // Configuration de build optimisée
  build: {
    target: 'es2015',
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: process.env.NODE_ENV === 'development',
    minify: 'terser',
    
    // Configuration du chunking pour optimiser le cache
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks
          'react-vendor': ['react', 'react-dom'],
          'ui-vendor': ['lucide-react', 'framer-motion'],
          
          // Feature chunks
          'api-services': ['./src/services/api.js']
        },
        
        // Nommage des chunks pour un cache optimal
        chunkFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.')
          const ext = info[info.length - 1]
          
          if (/\.(png|jpe?g|svg|gif|tiff|bmp|ico)$/i.test(assetInfo.name)) {
            return `images/[name]-[hash].${ext}`
          }
          
          if (/\.css$/i.test(assetInfo.name)) {
            return `css/[name]-[hash].${ext}`
          }
          
          return `assets/[name]-[hash].${ext}`
        }
      }
    },
    
    // Optimisation des assets
    assetsInlineLimit: 4096, // 4kb
    cssCodeSplit: true,
    emptyOutDir: true
  },
  
  // Optimisation des dépendances
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'lucide-react',
      'framer-motion'
    ]
  },
  
  // Configuration des variables d'environnement
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString())
  }
})
