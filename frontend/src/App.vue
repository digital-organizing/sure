<script setup lang="ts">
import { computed, onActivated, onMounted, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { useAccount } from './composables/useAccount'
import InternalMenuBar from './components/InternalMenuBar.vue'
import { useTitle } from '@vueuse/core'
import { useTexts } from './composables/useTexts'
import { usePrimeVue } from 'primevue/config'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import ConfirmDialog from 'primevue/confirmdialog'

const primevue = usePrimeVue()

const { account } = useAccount()
const route = useRoute()
const router = useRouter()
const toast = useToast()

const { getText, texts, onLanguageChange } = useTexts()

const sessionExpiredText = getText(
  'session-expired',
  'Your session has ended. Please log in again.',
)

// The session can end while a protected page is open (it expired, or the user
// logged out in another tab). Say so and go to the login, instead of leaving a
// page behind on which nothing works anymore.
watch(
  () => !!account.value.username && !!account.value.verified,
  (verified, wasVerified) => {
    if (verified || !wasVerified) return
    if (!route.matched.some((record) => record.meta.requiresAuth === true)) return
    toast.add({ severity: 'warn', summary: sessionExpiredText.value, life: 10000 })
    router.replace({ name: 'login', query: { next: route.fullPath } })
  },
)

const showInternalMenu = computed(() => route.meta.showInternalMenu !== false)

function setupPrimeVue() {
  if (primevue.config.locale) {
    Object.keys(primevue.config.locale).forEach((key) => {
      if (key in texts.value && primevue.config.locale && texts.value[key] !== undefined) {
        ;(primevue.config.locale as unknown as Record<string, string>)[key] = texts.value[key]
      }
    })
  }
}

onActivated(() => {
  useTitle(getText('sure_app_title'))
})

onMounted(() => {
  setupPrimeVue()
  onLanguageChange(() => {
    setupPrimeVue()
  })
})
</script>

<template>
  <InternalMenuBar v-if="account.verified && showInternalMenu" />
  <Toast />
  <ConfirmDialog></ConfirmDialog>
  <RouterView :key="$route.fullPath" />
  <footer>
    <div class="container">
      <div class="left">
        <nav>
          <a :href="getText('privacy-url').value">{{ getText('privacy-policy') }}</a>
          <a href="/about">{{ getText('about') }}</a>
        </nav>
      </div>
      <div class="right">
        <span
          ><a href="https://aids.ch">{{ getText('aids-hilfe-schweiz') }}</a></span
        >
      </div>
    </div>
  </footer>
</template>

<style scoped>
footer {
  background: black;
  color: white;
  padding-top: 4rem;
  padding-bottom: 3rem;
  margin-top: 5rem;
}
.container {
  display: flex;
  justify-content: space-between;
  gap: 2rem;
  width: 90%;
  margin: 0 auto;
  max-width: 700px;
}

footer .left,
footer .right {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

footer .left nav {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

footer a {
  color: white;
  text-decoration: none;
}
footer a:hover {
  text-decoration: underline;
}

h4 {
  margin: 0;
}

footer .right {
  align-items: flex-end;
  justify-content: flex-end;
}
</style>
