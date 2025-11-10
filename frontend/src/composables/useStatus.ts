import { sureApiGetCaseStatusOptions, type OptionSchema } from '@/client'
import { ref } from 'vue'
import { createGlobalState } from '@vueuse/core'

export const useStatus = createGlobalState(() => {
  const statusChoices = ref<OptionSchema[]>([])
  const error = ref<string | null>(null)

  function fetchStatusChoices() {
    sureApiGetCaseStatusOptions()
      .then((response) => {
        if (response.data) {
          statusChoices.value = response.data!
        }
      })
      .catch((error) => {
        console.error('Failed to fetch status choices:', error)
      })
  }

  function labelForStatus(value: string): string {
    const status = statusChoices.value.find((status) => status.value === value)
    return status ? status.label : value
  }

  fetchStatusChoices()

  return {
    statusChoices,
    error,
    fetchStatusChoices,
    labelForStatus,
  }
})
