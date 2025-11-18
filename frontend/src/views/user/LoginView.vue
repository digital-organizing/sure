<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { watch } from 'vue'
import { InputText } from 'primevue'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const { login, account, login2fa, error, twoFaDevices, logout } = useAccount()

const showLogin = computed(() => {
  return account.value.username === null
})

const showOtp = computed(() => {
  return account.value.username !== null && account.value.verified === false
})

const hasOtpDevices = computed(() => {
  return twoFaDevices.value.length > 0
})

watch([showLogin, showOtp, hasOtpDevices], ([newShowLogin, newShowOtp, newHasOtpDevices]) => {
  if (!newShowLogin && !newShowOtp && newHasOtpDevices) {
    const next = router.currentRoute.value.query.next as string | undefined
    router.push(next || { name: 'home' })
  }
  if (!newShowLogin && !newShowOtp && !newHasOtpDevices) {
    router.push({ name: 'setup-2fa' })
  }
})

async function onSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (e.valid) {
    await login(e.values['username'], e.values['password'])
  }
}

async function on2FaSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (e.valid) {
    const deviceId = e.values['device'] || twoFaDevices.value[0]?.id || ''
    const token = e.values['token']
    const remember = !!e.values['remember']

    await login2fa(token, deviceId, remember)

    if (account.value.username && account.value.verified) {
      const next = router.currentRoute.value.query.next as string | undefined
      router.push(next || { name: 'home' })
    }
  }
}
async function cancelLogin() {
  await logout()
}
</script>

<template>
  <h2>Login</h2>
  <Form @submit="onSubmit" v-if="showLogin" class="form-col">
    <FloatLabel variant="in">
      <label for="username">Username</label>
      <InputText name="username" id="username" />
    </FloatLabel>
    <FloatLabel variant="in">
      <label for="password">Password</label>
      <InputText type="password" name="password" id="password" />
    </FloatLabel>

    <Button type="submit" label="Login" />
    <Message severity="error" v-if="error">{{ error }}</Message>
  </Form>
  <Form @submit="on2FaSubmit" v-if="showOtp" class="form-col">
    <FloatLabel variant="in" v-if="twoFaDevices.length >= 2">
      <Select
        :options="twoFaDevices"
        :default-value="twoFaDevices[0].id"
        option-label="name"
        option-value="id"
        name="device"
        id="device"
      ></Select>
      <label for="device">Select 2FA Device</label>
    </FloatLabel>
    <FloatLabel variant="in">
      <label for="token">Enter Token</label>
      <InputText name="token" id="token" />
    </FloatLabel>
    <CheckboxGroup name="ingredient" class="toggle">
      <ToggleSwitch label="Remember this device" name="remember" />
      <label for="remember">Trust this device</label>
    </CheckboxGroup>
    <Button type="submit" label="Verify 2FA" />
    <Button label="Cancel" class="p-button-secondary" @click="cancelLogin" />
    <Message severity="error" v-if="error">{{ error }}</Message>
  </Form>
</template>
