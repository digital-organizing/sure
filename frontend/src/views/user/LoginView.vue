<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { InputText } from 'primevue'
import { useRouter } from 'vue-router'

const router = useRouter()

const { login, account, error } = useAccount()

async function onSubmit(e: { values: Record<string, string>; valid: boolean }) {
  if (e.valid) {
    await login(e.values['username'], e.values['password'])
    if (account.value.username) {
      const next = router.currentRoute.value.query.next as string | undefined
      router.push(next || { name: 'home' })
    }
  }
}
</script>

<template>
  <Form @submit="onSubmit">
    <Message severity="error" v-if="error">{{ error }}</Message>
    <InputText placeholder="Username" name="username" />
    <InputText type="password" placeholder="Password" name="password" />

    <Button type="submit" label="Login" />
  </Form>
</template>
