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
import { useTexts } from './useTexts'

type ApiResult = { error?: unknown; response?: Response }

// Shown until the text is translated in the texts database.
const ERROR_TEXTS: Record<string, string> = {
  'auth-error-invalid-credentials': 'Invalid username or password.',
  'auth-error-invalid-token': 'This code is not valid. Check your authenticator app and try again.',
  'auth-error-locked-out':
    'Too many failed login attempts. This account is locked for up to {minutes} minutes. Contact your administrator if you need access sooner.',
  'auth-error-throttled': 'Too many failed attempts. Please wait {seconds} seconds and try again.',
  'auth-error-too-many-requests':
    'Too many requests. Access is temporarily blocked, try again later.',
  'auth-error-network': 'Could not reach the server. Check your connection and try again.',
  'auth-error-unexpected': 'Something went wrong (error {status}). Please try again.',
}

const ERROR_CODES: Record<string, string> = {
  invalid_credentials: 'auth-error-invalid-credentials',
  invalid_token: 'auth-error-invalid-token',
  locked_out: 'auth-error-locked-out',
  throttled: 'auth-error-throttled',
}

export const useAccount = createGlobalState(() => {
  const { texts } = useTexts()

  function errorText(slug: string, args: Record<string, string | number> = {}) {
    let text = texts.value[slug] || ERROR_TEXTS[slug] || slug
    for (const [key, value] of Object.entries(args)) {
      text = text.replaceAll(`{${key}}`, String(value))
    }
    return text
  }

  // Not every failure has the { error } body of the auth endpoints: blocks,
  // validation errors, server errors and network failures do not. Each of them
  // still has to end up as a message the user can see.
  function errorMessage(result: ApiResult): string {
    // response is undefined when the request never reached the server.
    if (!result.response) {
      return errorText('auth-error-network')
    }
    const body = (
      typeof result.error === 'object' && result.error !== null ? result.error : {}
    ) as {
      error?: unknown
      code?: unknown
      detail?: unknown
      retry_after?: unknown
    }
    const slug = typeof body.code === 'string' ? ERROR_CODES[body.code] : undefined
    if (slug) {
      const seconds = typeof body.retry_after === 'number' ? body.retry_after : 60
      return errorText(slug, { seconds, minutes: Math.ceil(seconds / 60) })
    }
    if (result.response.status === 429) {
      return errorText('auth-error-too-many-requests')
    }
    if (typeof body.error === 'string' && body.error) {
      return body.error
    }
    if (typeof body.detail === 'string' && body.detail) {
      return body.detail
    }
    return errorText('auth-error-unexpected', { status: result.response.status })
  }

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
        throw new Error(errorMessage(response))
      }
      account.value = response.data
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function setInitialPassword(password: string, sesame: string, email: string) {
    loading.value = true
    error.value = null
    const response = await coreApiSetInitialPassword({
      body: { new_password: password, email: email },
      query: { sesame: sesame },
    })
    if (response === null) {
      return null
    }
    // response is undefined when the request never reached the server.
    if (response.response?.status !== 200) {
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
        throw new Error(errorMessage(response))
      }
      twoFaDevices.value = response.data || []
    } catch (e: unknown) {
      console.error(e)
      error.value = (e as Error).message
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
        throw new Error(errorMessage(response))
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
        throw new Error(errorMessage(response))
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
        throw new Error(errorMessage(response))
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
        throw new Error(errorMessage(response))
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
      await Promise.all([fetchAccount(), fetchTwoFaDevices()])

      if (response.error) {
        return false
      }
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
    return true
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
