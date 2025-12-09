<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAccount } from './composables/useAccount'
import InternalMenuBar from './components/InternalMenuBar.vue'
import { useTitle } from '@vueuse/core'
import { useTexts } from './composables/useTexts'
import { usePrimeVue } from 'primevue/config'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'

const primevue = usePrimeVue()

const { account } = useAccount()
const route = useRoute()

const { getText, texts, onLanguageChange } = useTexts()

const showInternalMenu = computed(() => route.meta.showInternalMenu !== false)

useTitle(getText('sure_app_title'))

function setupPrimeVue() {
  if (primevue.config.locale) {
    Object.keys(primevue.config.locale).forEach((key) => {
      if (key in texts.value && primevue.config.locale) {
        ;(primevue.config.locale as unknown as Record<string, string>)[key] = texts.value[key]
      }
    })
  }
}

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
