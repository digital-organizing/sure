import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { resolve } from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': resolve('./src')
    },
  },
  base: '/static/',
  publicDir: 'public',
  build: {
    manifest: "manifest.json",
    rollupOptions: {
      input: {
        main: 'src/main.ts',
      }
    }
  },
  root: resolve('.'),

})
