<script lang="ts" setup>
import { type OtpDeviceResponse } from '@/client'
import { useAccount } from '@/composables/useAccount'
import { useClipboard } from '@vueuse/core'
import { useQRCode } from '@vueuse/integrations/useQRCode'
import { useToast } from 'primevue/usetoast'
import { computed, ref } from 'vue'

import { useRouter } from 'vue-router'

const router = useRouter()

const { copy, isSupported } = useClipboard()
const toast = useToast()

const name = ref('SURE 2FA')
const device = ref<OtpDeviceResponse | null>(null)
const configUrl = computed(() => (device.value ? device.value.config_url || '' : ''))

const configCode = useQRCode(configUrl)

const { account, setup2faDevice, verifyOtp, createBackupCodes, twoFaDevices } = useAccount()

const codes = ref<string[]>([])

const setupComplete = computed(() => {
  return (account.value?.otp && twoFaDevices.value.length > 0) || false
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
  toast.add({
    severity: 'success',
    summary: '2FA Setup',
    detail: 'Two-Factor Authentication setup complete!',
    life: 3000,
  })
}

async function onCreateBackupCodes() {
  const newCodes = await createBackupCodes()
  if (newCodes && newCodes.length > 0) {
    codes.value = newCodes
  }
}
function onCopyCode() {
  copy(device.value?.config_url || '').then(() => {
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: '2FA configuration URL copied to clipboard',
      life: 3000,
    })
  })
}
</script>

<template>
  <Form @submit="onCreateDevice" v-if="!device && !setupComplete" class="form-col">
    <p>
      To enhance the security of your account, please set up Two-Factor Authentication (2FA). Start
      by creating a new 2FA device.
    </p>
    <FloatLabel variant="in">
      <label for="device_name">Device Name</label>
      <InputText label="Device Name" v-model="name" name="device_name" id="device_name" />
    </FloatLabel>
    <Button type="submit">Create 2FA Device</Button>
  </Form>

  <Form v-if="configUrl && !setupComplete" @submit="onVerify2FaSetup" class="form-col">
    <p>Scan the QR code below with your authenticator app:</p>
    <img :src="configCode" alt="2FA QR Code" class="qr-code" />
    <span>Or use this code: </span>
    <div class="code-box">
      <span>
        <InputText :value="device?.config_url" readonly />
      </span>
      <Button icon="pi pi-copy" text @click="onCopyCode" v-if="isSupported"></Button>
    </div>
    <FloatLabel variant="in">
      <label for="auth_code">Enter Code </label>
      <InputText name="auth_code" id="auth_code" />
    </FloatLabel>
    <Button type="submit">Verify 2FA Setup</Button>
    <p>
      You can Download an authenticator app like Google Authenticator or Authy to scan the QR code:
    </p>
    <ul>
      <li>
        <a
          href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2"
          target="_blank"
          >Google Authenticator</a
        >
      </li>
      <li><a href="https://authy.com/download/" target="_blank">Authy</a></li>
    </ul>
  </Form>

  <Form v-if="setupComplete" @submit="onCreateBackupCodes" class="form-col">
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
