<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { watch } from 'vue'
import { InputText } from 'primevue'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const { login, account, login2fa, error, twoFaDevices } = useAccount()

const showLogin = computed(() => {
  return account.value.username === null
})

const showOtp = computed(() => {
  return account.value.username !== null && account.value.verified === false
})

watch([showLogin, showOtp], ([newShowLogin, newShowOtp]) => {
  if (!newShowLogin && !newShowOtp) {
    const next = router.currentRoute.value.query.next as string | undefined
    router.push(next || { name: 'home' })
  }
})

async function onSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (e.valid) {
    await login(e.values['username'], e.values['password'])
    if (account.value.username && account.value.verified) {
      const next = router.currentRoute.value.query.next as string | undefined
      router.push(next || { name: 'home' })
    }
    if (twoFaDevices.value.length == 0) {
      router.push({ name: 'setup-2fa' })
    }
  }
}

async function on2FaSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (e.valid) {
    const deviceId = e.values['device'] || twoFaDevices.value[0]?.id || ''
    const token = e.values['token']
    const remember = !!e.values['remember']
    console.log('Remember device:', remember)

    await login2fa(token, deviceId, remember)

    if (account.value.username && account.value.otp) {
      const next = router.currentRoute.value.query.next as string | undefined
      router.push(next || { name: 'home' })
    }
  }
}
</script>

<template>
  <Form @submit="onSubmit" v-if="showLogin">
    <Message severity="error" v-if="error">{{ error }}</Message>
    <InputText placeholder="Username" name="username" />
    <InputText type="password" placeholder="Password" name="password" />

    <Button type="submit" label="Login" />
  </Form>
  <Form @submit="on2FaSubmit" v-if="showOtp">
    <Select
      :options="twoFaDevices"
      option-label="name"
      option-value="id"
      name="device"
      v-if="twoFaDevices.length >= 2"
    ></Select>
    <InputText placeholder="2FA Token" name="token" />
    <CheckboxGroup name="ingredient" class="flex flex-wrap gap-4">
      <ToggleSwitch label="Remember this device" name="remember" />
    </CheckboxGroup>
    <Button type="submit" label="Verify 2FA" />
  </Form>
</template>
