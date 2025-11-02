import './assets/main.css'
import 'vite/modulepreload-polyfill'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { client } from './client/client.gen.ts'
import { coreApiGetCsrfToken } from './client/sdk.gen.ts'

import PrimeVue from 'primevue/config'
import Material from '@primeuix/themes/material'
import { $dt, definePreset } from '@primeuix/themes'

import '@/assets/base.css'

import * as Sentry from '@sentry/vue'
import { createSentryPiniaPlugin } from '@sentry/vue'

// Import stores for initialization

function getCsrfToken() {
  return (
    document.cookie
      ?.split(';')
      .find((c) => c.trim().startsWith('csrftoken='))
      ?.split('=')[1] || ''
  )
}

// Add CSRF token to all requests
client.interceptors.request.use(async (request) => {
  const url = new URL(request.url)
  if (url.pathname.startsWith('/api/csrf') || url.pathname.startsWith('/api/login')) {
    return request
  }
  let token = getCsrfToken()
  if (!token) {
    // Make request to get the token
    await coreApiGetCsrfToken()
    token = getCsrfToken()
  }
  request.headers.append('X-CSRFToken', token)
  return request
})

client.interceptors.response.use(async (response) => {
  if (response.status == 401) {
    router.push({ name: 'login' })
  }
  return response
})

const app = createApp(App)

// Defining custom theme preset, unclear if this is the best way to do this
const SurePreset = definePreset(Material, {
  components: {
    button: {
      extend: {
        hover: {
          backgroundColor: $dt('--color-ahs-middle-gray').value,
          borderColor: 'var(--color-semantic-primary-600)',
        },
      },
    },
  },
  utilities: {},
  semantic: {
    primary: {
      50: '#FFE5E7',
      100: '#FFC6C9',
      200: '#FF9BA0',
      300: '#FF6E77',
      400: '#F53A4B',
      500: '#E20613',
      600: '#C70510',
      700: '#A0040D',
      800: '#7A030A',
      900: '#530207',
      950: '#2E0104',
    },
    secondary: {
      50: '#ffffff',
      100: '#646464',
      200: '#646464',
      300: '#646464',
      400: '#646464',
      500: '#646464',
      600: '#646464',
      700: '#646464',
      800: '#646464',
      900: '#646464',
      950: '#646464',
    },
    colorScheme: {
      light: {
        semantic: {
          background: '#E20613',
        },
      },
    },
  },
})

Sentry.init({
  app,
  dsn: 'https://f23eef026dedb9d752fc45fc961f71a0@sentry.d-o.li/5',
  tracesSampleRate: 1.0,
  sendDefaultPii: true,
})

const pinia = createPinia()

pinia.use(createSentryPiniaPlugin())

app.use(pinia)
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: SurePreset,
    options: {
      darkModeSelector: '.dark',
    },
  },
})

// Initialize stores after Pinia is set up
const initializeStores = () => {
  // Initialize key stores

  // Stores are automatically initialized when accessed
  console.log('Pinia stores initialized')
}

app.mount('#app')

// Initialize stores after app is mounted
initializeStores()
