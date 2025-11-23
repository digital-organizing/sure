import './assets/main.css'
import 'vite/modulepreload-polyfill'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { client } from './client/client.gen.ts'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'

import PrimeVue from 'primevue/config'
import Material from '@primeuix/themes/material'
import { definePreset } from '@primeuix/themes'

import '@/assets/base.css'
import './assets/main.css'

import * as Sentry from '@sentry/vue'
import { createSentryPiniaPlugin } from '@sentry/vue'

// Import stores for initialization

function getCookie(name: string) {
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}
let token = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)?.value || ''

// Add CSRF token to all requests
client.interceptors.request.use(async (request) => {
  const url = new URL(request.url)
  if (url.pathname.startsWith('/api/csrf')) {
    return request
  }
  request.headers.append('X-CSRFToken', token)
  return request
})

client.interceptors.response.use(async (response) => {
  if (response.status == 401) {
    if (router.currentRoute.value.name !== 'login') {
      router.push({ path: '/login', query: { next: router.currentRoute.value.fullPath } })
    }
  }
  token = getCookie('csrftoken') || token
  return response
})

const app = createApp(App)

// Defining custom theme preset, unclear if this is the best way to do this
const SurePreset = definePreset(Material, {
  components: {
    button: {
      colorScheme: {
        light: {
          root: {
            primary: {
              hoverBackground: 'var(--color-ahs-black)',
              hoverColor: 'var(--color-ahs-white)',
              hoverBorderColor: 'var(--color-ahs-black)',
              background: 'var(--color-ahs-red)',
              color: 'var(--color-ahs-white)',
              borderColor: 'var(--color-ahs-red)',
              activeBackground: 'var(--color-ahs-red)',
            },
            secondary: {
              borderColor: 'var(--color-ahs-middle-gray)',
              color: 'var(--color-ahs-middle-gray)',
              background: 'var(--color-ahs-white)',
              hoverBackground: 'var(--color-ahs-light-gray)',
              hoverColor: 'var(--color-ahs-black)',
              hoverBorderColor: 'var(--color-ahs-middle-gray)',
            },
          },
          outlined: {
            secondary: {
              borderColor: 'var(--color-ahs-middle-gray)',
              color: 'var(--color-ahs-middle-gray)',
              hoverBackground: 'var(--color-ahs-white)',
            },
          },
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
      100: '#E0E0E0',
      200: '#bcbcbc',
      300: '#A8A8A8',
      400: '#929292',
      500: '#646464',
      600: '#565656',
      700: '#3c3c3c',
      800: '#242424',
      900: '#161616',
      950: '#080808',
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
app.use(ToastService)
app.use(ConfirmationService)

// Initialize stores after Pinia is set up
const initializeStores = () => {
  // Initialize key stores
  // Stores are automatically initialized when accessed
}

app.mount('#app')

// Initialize stores after app is mounted
initializeStores()
