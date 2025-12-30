import { sureApiGetCaseStatusOptions, type OptionSchema } from '@/client'
import { ref } from 'vue'
import { createGlobalState } from '@vueuse/core'
import { useTexts } from './useTexts'

export const useStatus = createGlobalState(() => {
  const statusChoices = ref<OptionSchema[]>([])
  const error = ref<string | null>(null)
  
  const { onLanguageChange } = useTexts()

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

  function indexForStatus(value: string): number {
    return statusChoices.value.findIndex((status) => status.value === value)
  }
  
  onLanguageChange(() => {
    fetchStatusChoices()
  })

  fetchStatusChoices()

  return {
    statusChoices,
    error,
    fetchStatusChoices,
    indexForStatus,
    labelForStatus,
  }
})
