<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAccount } from './composables/useAccount'
import InternalMenuBar from './components/InternalMenuBar.vue'
import { useTitle } from '@vueuse/core'
import { useTexts } from './composables/useTexts'
import { usePrimeVue } from 'primevue/config'

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
  <RouterView />
</template>

<style scoped></style>
