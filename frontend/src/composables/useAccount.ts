import { coreApiAccount, coreApiLoginView, coreApiLogoutView } from '@/client'
import { computed, ref } from 'vue'

export function useAccount() {
  const account = ref<{
    username: string | null
    is_staff: boolean | null
    is_superuser: boolean | null
  }>({
    username: null,
    is_staff: null,
    is_superuser: null,
  })
  const loading = ref(false)
  const error = ref<string | null>(null)

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
      account.value = {
        username: response.data.username,
        is_staff: response.data.is_staff!,
        is_superuser: response.data.is_superuser!,
      }
    } catch (e) {
      console.error(e)
      error.value = 'Failed to fetch account information: ' + e.message
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
        throw new Error(response.error!.message)
      }
      await fetchAccount()
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }

    return account.value
  }

  async function logout() {
    loading.value = true
    error.value = null
    try {
      await coreApiLogoutView()
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

  fetchAccount()

  return {
    account,
    loading,
    error,
    fetchAccount,
    isAuthenticated,
    login,
    logout,
    interval,
  }
}
