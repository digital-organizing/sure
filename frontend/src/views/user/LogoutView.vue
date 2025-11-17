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
  <Form @submit="onLogout" class="form-col">
    <p>Are you sure you want to logout?</p>
    <CheckboxGroup name="ingredient" class="toggle">
      <ToggleSwitch name="forget" label="Forget this device for 2FA" id="forget" />
      <label for="forget">Forget this device for 2FA</label>
    </CheckboxGroup>

    <Button type="submit" label="Logout" />
    <Button label="Cancel" @click="router.back()" severity="secondary"></Button>
  </Form>
</template>
