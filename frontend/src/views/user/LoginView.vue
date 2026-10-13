<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { useTexts } from '@/composables/useTexts'
import { nextTick, onMounted } from 'vue'
import { InputText } from 'primevue'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { getText: t } = useTexts()

const { login, account, login2fa, error, twoFaDevices, logout, fetchTwoFaDevices } = useAccount()

const helpText = t(
  'login-help',
  'Forgot your password or lost access to your authenticator app? Contact your administrator.',
)

const showLogin = computed(() => {
  return account.value.username === null
})

const showOtp = computed(() => {
  return account.value.username !== null && account.value.verified === false
})

const hasOtpDevices = computed(() => {
  return twoFaDevices.value.length > 0
})

// The router guard has loaded the account and has already sent verified users
// on, so only the half logged in ones (password but no 2FA yet) are left.
onMounted(async () => {
  if (!account.value.username) {
    return
  }

  await fetchTwoFaDevices()

  if (!hasOtpDevices.value) {
    router.replace({ name: 'setup-2fa' })
    return
  }
})

// replace instead of push: the login must not stay in the history, or the back
// button leads to a page that immediately sends the user forward again.
function continueAfterLogin() {
  const next = router.currentRoute.value.query.next as string | undefined
  router.replace(next || { name: 'home' })
}

async function onSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (e.valid) {
    await login(e.values['username']!, e.values['password']!)
    nextTick(() => {
      if (!showLogin.value && !showOtp.value && hasOtpDevices.value) {
        continueAfterLogin()
      }
      if (!showLogin.value && !hasOtpDevices.value) {
        router.replace({ name: 'setup-2fa' })
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
      continueAfterLogin()
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
    <p class="help">{{ helpText }}</p>
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
    <p class="help">{{ helpText }}</p>
  </Form>
</template>

<style scoped>
.help {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  margin: 0;
}
</style>
