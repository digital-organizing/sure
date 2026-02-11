<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { useTexts } from '@/composables/useTexts'
import { nextTick, onMounted } from 'vue'
import { InputText } from 'primevue'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { getText: t } = useTexts()

const { login, account, login2fa, error, twoFaDevices, logout, fetchAccount, fetchTwoFaDevices } =
  useAccount()

const showLogin = computed(() => {
  return account.value.username === null
})

const showOtp = computed(() => {
  return account.value.username !== null && account.value.verified === false
})

const hasOtpDevices = computed(() => {
  return twoFaDevices.value.length > 0
})

onMounted(async () => {
  if (!account.value.username) {
    await fetchAccount()
  }

  if (!account.value.username) {
    return
  }

  if (account.value.username && account.value.verified) {
    const next = router.currentRoute.value.query.next as string | undefined
    router.push(next || { name: 'home' })
    return
  }

  await fetchTwoFaDevices()

  if (!hasOtpDevices.value) {
    router.push({ name: 'setup-2fa' })
    return
  }
})

async function onSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (e.valid) {
    await login(e.values['username']!, e.values['password']!)
    nextTick(() => {
      console.log('account after login', account.value)
      console.log('showLogin', showLogin.value)
      console.log('showOtp', showOtp.value)
      console.log('hasOtpDevices', hasOtpDevices.value)
      if (!showLogin.value && !showOtp.value && hasOtpDevices.value) {
        const next = router.currentRoute.value.query.next as string | undefined
        router.push(next || { name: 'home' })
      }
      if (!showLogin.value && !hasOtpDevices.value) {
        router.push({ name: 'setup-2fa' })
      }
    })
  }
}

async function on2FaSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (e.valid) {
    const deviceId = e.values['device'] || twoFaDevices.value[0]?.id || ''
    const token = e.values['token']
    const remember = !!e.values['remember']

    await login2fa(token!, deviceId, remember)

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
  <div>
    <Button as-child v-slot="slotProps" severity="primary">
      <RouterLink :to="{ name: 'results' }" :class="slotProps.class">
        {{ t('check-your-results') }}
      </RouterLink>
    </Button>
  </div>
  <h2>{{ t('login') }}</h2>
  <Form @submit="onSubmit" v-if="showLogin" class="form-col">
    <FloatLabel variant="in">
      <label for="username">{{ t('username') }}</label>
      <InputText name="username" id="username" />
    </FloatLabel>
    <FloatLabel variant="in">
      <label for="password">{{ t('password') }}</label>
      <InputText type="password" name="password" id="password" />
    </FloatLabel>

    <Button type="submit" :label="t('login').value" />
    <Message severity="error" v-if="error">{{ error }}</Message>
  </Form>

  <Form @submit="on2FaSubmit" v-if="showOtp" class="form-col">
    <FloatLabel variant="in" v-if="twoFaDevices.length >= 2">
      <Select
        :options="twoFaDevices"
        :default-value="twoFaDevices[0]!.id"
        option-label="name"
        option-value="id"
        name="device"
        id="device"
      ></Select>
      <label for="device">{{ t('select-2fa-device') }}</label>
    </FloatLabel>
    <FloatLabel variant="in">
      <label for="token">{{ t('enter-token') }}</label>
      <InputText name="token" id="token" />
    </FloatLabel>
    <CheckboxGroup name="ingredient" class="toggle">
      <ToggleSwitch :label="t('trust-device').value" name="remember" />
      <label for="remember">{{ t('trust-device') }}</label>
    </CheckboxGroup>
    <Button type="submit" :label="t('verify-2fa').value" />
    <Button :label="t('cancel').value" class="p-button-secondary" @click="cancelLogin" />
    <Message severity="error" v-if="error">{{ error }}</Message>
  </Form>
</template>
