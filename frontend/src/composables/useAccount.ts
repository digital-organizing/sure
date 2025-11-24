import {
  coreApiAccount,
  coreApiGenerateOtpBackupCodesView,
  coreApiListOtpDevicesView,
  coreApiLoginView,
  coreApiLogoutView,
  coreApiOtp2FaChallengeView,
  coreApiSetInitialPassword,
  coreApiSetupOtpView,
  coreApiVerifyOtpView,
  type AccountResponse,
  type LoginResponse,
} from '@/client'
import { createGlobalState } from '@vueuse/core'
import { computed, ref } from 'vue'

export const useAccount = createGlobalState(() => {
  const account = ref<AccountResponse>({
    username: null,
  })
  const loading = ref(false)
  const error = ref<string | null>(null)
  const twoFaDevices = ref<Array<{ id: string; name: string }>>([])

  const isAuthenticated = computed(() => {
    return account.value.username !== null
  })

  async function fetchAccount() {
    loading.value = true
    error.value = null
    try {
      const response = await coreApiAccount()
      if (!response.data) {
        throw new Error('No username in response')
      }
      account.value = response.data
    } catch (e: unknown) {
      error.value = 'Failed to fetch account information: ' + (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function setInitialPassword(password: string, sesame: string, email: string) {
    loading.value = true
    error.value = null
    const response = await coreApiSetInitialPassword({
      body: { new_password: password, sesame: sesame, email: email },
    })
    if (response === null) {
      return null
    }
    if (response.response.status !== 200) {
      error.value = 'Failed to set initial password'
      return response.error as LoginResponse
    }
    loading.value = false
    error.value = null
  }

  async function fetchTwoFaDevices() {
    loading.value = true
    error.value = null
    try {
      const response = await coreApiListOtpDevicesView()
      if (response.error) {
        throw new Error(response.error.error!)
      }
      twoFaDevices.value = response.data || []
    } catch (e: unknown) {
      console.error(e)
      error.value = 'Failed to fetch 2FA devices: ' + (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function createBackupCodes() {
    loading.value = true
    error.value = null
    try {
      const response = await coreApiGenerateOtpBackupCodesView()
      if (response.error) {
        throw new Error(response.error.error!)
      }
      return response.data
    } catch (e: unknown) {
      error.value = (e as Error).message
      return null
    } finally {
      loading.value = false
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const response = await coreApiLoginView({
        body: {
          username,
          password,
        },
      })
      if (response.error) {
        throw new Error(response.error.error!)
      }
      await Promise.all([fetchTwoFaDevices(), fetchAccount()])
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }

    return account.value
  }

  async function setup2faDevice(name: string) {
    loading.value = true
    error.value = null
    try {
      const response = await coreApiSetupOtpView({ body: { name } })
      if (response.error) {
        throw new Error(response.error.error!)
      }
      return response.data
    } catch (e: unknown) {
      error.value = (e as Error).message
      return null
    } finally {
      loading.value = false
    }
  }

  async function login2fa(token: string, device_id: string, remember: boolean) {
    loading.value = true
    error.value = null
    try {
      const response = await coreApiOtp2FaChallengeView({ body: { token, device_id, remember } })
      if (response.error) {
        throw new Error(response.error.error!)
      }
      await fetchAccount()
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
    return account.value
  }

  async function verifyOtp(token: string, device_id: string) {
    loading.value = true
    error.value = null
    try {
      const response = await coreApiVerifyOtpView({ body: { token, device_id } })
      if (response.error) {
        throw new Error(response.error.error!)
      }

      await Promise.all([fetchAccount(), fetchTwoFaDevices()])
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function logout(forget: boolean = false) {
    loading.value = true
    error.value = null
    try {
      await coreApiLogoutView({ body: { forget } })
      account.value = {
        username: null,
        is_staff: null,
        is_superuser: null,
      }
    } catch (e) {
      error.value = 'Failed to logout: ' + e
    } finally {
      loading.value = false
    }
  }

  const interval = setInterval(
    () => {
      fetchAccount()
    },
    5 * 60 * 1000,
  )

  fetchAccount().then(() => {
    if (isAuthenticated.value) {
      fetchTwoFaDevices()
    }
  })

  return {
    account,
    loading,
    error,
    fetchAccount,
    isAuthenticated,
    login,
    logout,
    login2fa,
    setup2faDevice,
    twoFaDevices,
    verifyOtp,
    interval,
    setInitialPassword,
    createBackupCodes,
    fetchTwoFaDevices,
  }
})
