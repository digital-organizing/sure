import { sentryVitePlugin } from "@sentry/vite-plugin";
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { resolve } from 'node:path'
import Components from 'unplugin-vue-components/vite';
import {PrimeVueResolver} from '@primevue/auto-import-resolver';

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools(), sentryVitePlugin({
    org: "d-o",
    project: "sure",
    url: "https://sentry.d-o.li"
  }),
  Components({
    resolvers: [PrimeVueResolver()],
  })
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
    },

    sourcemap: true
  },
  root: resolve('.'),

})