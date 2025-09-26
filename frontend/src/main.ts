import './assets/main.css'
import 'vite/modulepreload-polyfill'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { client } from './client/client.gen.ts'
import { coreApiGetCsrfToken } from './client/sdk.gen.ts'

import PrimeVue from 'primevue/config';
import Aura from '@primeuix/themes/aura';

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

const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(PrimeVue, {
    theme: {
        preset: Aura
    }
});

// Initialize stores after Pinia is set up
const initializeStores = () => {
  // Initialize key stores

  // Stores are automatically initialized when accessed
  console.log('Pinia stores initialized')
}

app.mount('#app')

// Initialize stores after app is mounted
initializeStores()
