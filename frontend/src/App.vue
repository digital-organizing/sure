<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useAccount } from './composables/useAccount'
import InternalMenuBar from './components/InternalMenuBar.vue'

const { account } = useAccount()
</script>

<template>
  <InternalMenuBar v-if="account.verified" />
  <Toast />
  <RouterView />
</template>

<style scoped></style>
