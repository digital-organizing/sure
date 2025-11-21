<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAccount } from './composables/useAccount'
import InternalMenuBar from './components/InternalMenuBar.vue'

const { account } = useAccount()
const route = useRoute()

const showInternalMenu = computed(() => route.meta.showInternalMenu !== false)
</script>

<template>
  <InternalMenuBar v-if="account.verified && showInternalMenu" />
  <Toast />
  <ConfirmDialog></ConfirmDialog>
  <RouterView />
</template>

<style scoped></style>
