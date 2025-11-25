<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAccount } from './composables/useAccount'
import InternalMenuBar from './components/InternalMenuBar.vue'
import { useTitle } from '@vueuse/core'
import { useTexts } from './composables/useTexts'

const { account } = useAccount()
const route = useRoute()

const { getText } = useTexts()

const showInternalMenu = computed(() => route.meta.showInternalMenu !== false)

useTitle(getText('sure_app_title'))
</script>

<template>
  <InternalMenuBar v-if="account.verified && showInternalMenu" />
  <Toast />
  <ConfirmDialog></ConfirmDialog>
  <RouterView />
</template>

<style scoped></style>
