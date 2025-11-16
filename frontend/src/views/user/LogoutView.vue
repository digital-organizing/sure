<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { useRouter } from 'vue-router'

const router = useRouter()
const { logout } = useAccount()

function onLogout(e: { values: Record<string, boolean>; valid: boolean }) {
  logout(e.values.forget).then(() => {
    router.push({ name: 'login' })
  })
}
</script>

<template>
  <Form @submit="onLogout">
    <p>Are you sure you want to logout?</p>
    <ToggleSwitch name="forget" label="Forget this device for 2FA" />
    <Button type="submit" label="Logout" />
  </Form>
</template>
