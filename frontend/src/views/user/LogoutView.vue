<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { useRouter } from 'vue-router'

const router = useRouter()
const { logout } = useAccount()

function onLogout() {
  logout().then(() => {
    router.push({ name: 'login' })
  })
}
</script>

<template>
  <Button @click="onLogout" label="Logout" />
</template>
