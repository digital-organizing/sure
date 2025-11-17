<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { useUrlSearchParams } from '@vueuse/core'
import { ref } from 'vue'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const email = ref<string | null>(null)
const token = ref<string | null>(null)

const { setInitialPassword } = useAccount()

onMounted(() => {
  const params = useUrlSearchParams()
  email.value = Array.isArray(params.email) ? params.email[0] : params.email || null
  token.value = Array.isArray(params.sesame) ? params.sesame[0] : params.sesame || null
  console.log('Email:', email.value)
  console.log('Token:', token.value)

  if (!email.value || !token.value) {
    // Handle missing parameters
    console.error('Missing email or token in URL parameters')
    router.push({ name: 'Home' })
  }
})

async function onSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (!e.valid || !email.value || !token.value) {
    return
  }

  const password = e.values['password']
  const confirmPassword = e.values['confirm_password']

  if (password !== confirmPassword) {
    // Handle password mismatch
    console.error('Passwords do not match')
    return
  }

  await setInitialPassword(email.value, token.value, password)
  router.push({ name: 'setup-2fa' })
}
</script>

<template>
  <Form @submit="onSubmit">
    <Password label="Password" name="password" />
    <Password label="Confirm Password" name="confirm_password" />

    <Button type="submit">Set Password</Button>
  </Form>
</template>
