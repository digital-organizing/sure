<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { useTexts } from '@/composables/useTexts'
import type { FormResolverOptions } from '@primevue/forms'
import { useUrlSearchParams } from '@vueuse/core'
import { ref } from 'vue'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const email = ref<string | null>(null)
const token = ref<string | null>(null)

const errors = ref<string[]>([])
const { setInitialPassword, error, account, fetchAccount, fetchTwoFaDevices, twoFaDevices } =
  useAccount()

onMounted(() => {
  const params = useUrlSearchParams()
  email.value = Array.isArray(params.email) ? params.email[0]! : params.email || null
  token.value = Array.isArray(params.sesame) ? params.sesame[0]! : params.sesame || null

  if (!email.value || !token.value) {
    // Handle missing parameters
    router.push({ name: 'Home' })
  }
})

async function onSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (!e.valid || !email.value || !token.value) {
    return
  }

  const password = e.values['password']!

  const result = await setInitialPassword(password, token.value, email.value)
  if (result?.error) {
    error.value = result.error || ''
    return
  }
  await Promise.all([fetchAccount(), fetchTwoFaDevices()])
  if (account.value.verified && twoFaDevices.value.length > 0) {
    router.push({ name: 'home' })
  } else if (account.value.username && twoFaDevices.value.length == 0) {
    router.push({ name: 'setup-2fa' })
  } else if (account.value.username) {
    router.push({ name: 'login' }) // To complete the login flow
  }
}

function resolver(e: FormResolverOptions) {
  return {
    errors: {},
    values: e.values,
  }
}
const { getText: t } = useTexts()
</script>

<template>
  <Form @submit="onSubmit" class="form-col" :resolver="resolver">
    <p>
      {{ t('set-initial-password-instruction') }}
      <span class="email"> {{ email }}. </span>
    </p>
    <FloatLabel variant="in">
      <Password name="password" type="password" id="password" toggle-mask />
      <label for="password">{{ t('password') }}</label>
    </FloatLabel>

    <Button type="submit">{{ t('submit') }}</Button>

    <Message severity="error" v-if="errors.length || error">
      <strong>{{ error }}</strong>
      <ul v-if="errors.length > 0">
        <li v-for="(err, index) in errors" :key="index">{{ err }}</li>
      </ul>
    </Message>
  </Form>
</template>
