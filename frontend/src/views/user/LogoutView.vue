<script lang="ts" setup>
import { useAccount } from '@/composables/useAccount'
import { useTexts } from '@/composables/useTexts'
import { useRouter } from 'vue-router'

const router = useRouter()
const { logout } = useAccount()

const { getText: t } = useTexts()

function onLogout(e: { values: Record<string, boolean>; valid: boolean }) {
  logout(e.values.forget).then(() => {
    router.push({ name: 'login' })
  })
}
</script>

<template>
  <Form @submit="onLogout" class="form-col">
    <p>{{ t('are-you-sure-logout') }}</p>
    <CheckboxGroup name="ingredient" class="toggle">
      <ToggleSwitch name="forget" :label="t('forget-trust')" id="forget" />
      <label for="forget">{{ t('forget-trust') }}</label>
    </CheckboxGroup>

    <Button type="submit" :label="t('logout').value" />
    <Button :label="t('cancel').value" @click="router.back()" severity="secondary"></Button>
  </Form>
</template>
