<script lang="ts" setup>
import { type OtpDeviceResponse } from '@/client'
import { useAccount } from '@/composables/useAccount'
import { useQRCode } from '@vueuse/integrations/useQRCode'
import { computed, ref } from 'vue'

import { useRouter } from 'vue-router'

const router = useRouter()

const name = ref('SURE 2FA')
const device = ref<OtpDeviceResponse | null>(null)
const configUrl = computed(() => (device.value ? device.value.config_url || '' : ''))

const configCode = useQRCode(configUrl)

const { account, setup2faDevice, verifyOtp, createBackupCodes } = useAccount()

const codes = ref<string[]>([])

const setupComplete = computed(() => {
  return account.value?.otp || false
})

async function onCreateDevice(e: { values: Record<string, string>; valid: boolean }) {
  if (!e.valid) {
    return
  }

  const response = await setup2faDevice(name.value)
  if (!response || !response.config_url) {
    return
  }

  device.value = response
}

async function onVerify2FaSetup(e: { values: Record<string, string>; valid: boolean }) {
  if (!e.valid || !device.value) {
    return
  }

  const authCode = e.values['auth_code']
  await verifyOtp(authCode, device.value.id)
  router.push({ name: 'home' })
}

async function onCreateBackupCodes() {
  const newCodes = await createBackupCodes()
  if (newCodes && newCodes.length > 0) {
    codes.value = newCodes
  }
}
</script>

<template>
  <Form @submit="onCreateDevice" v-if="!device && !setupComplete">
    <InputText label="Device Name" v-model="name" name="device_name" />
    <Button type="submit">Create 2FA Device</Button>
  </Form>

  <Form v-if="configUrl && !setupComplete" @submit="onVerify2FaSetup">
    <p>Scan the QR code below with your authenticator app:</p>
    <img :src="configCode" alt="2FA QR Code" />
    <span>Or use this code: {{ configUrl }}</span>
    <InputText label="Enter Code from Authenticator App" name="auth_code" />
    <Button type="submit">Verify 2FA Setup</Button>
  </Form>

  <Form v-if="setupComplete" @submit="onCreateBackupCodes">
    <p>
      2FA setup is complete! Generate backup codes to ensure you can access your account if you lose
      your 2FA device.
    </p>
    <Button type="submit" v-if="codes.length == 0">Generate Backup Codes</Button>
    <div v-if="codes.length > 0">
      <h3>Your Backup Codes:</h3>
      <ul>
        <li v-for="code in codes" :key="code">{{ code }}</li>
      </ul>
      <p>Please store these codes in a safe place.</p>
    </div>
  </Form>

  <Button v-if="setupComplete" @click="router.push({ name: 'home' })">Go to Home</Button>
</template>
