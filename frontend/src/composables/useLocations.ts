import { ref } from 'vue'
import { createGlobalState } from '@vueuse/core'
import { tenantsApiListLocations, type LocationSchema } from '@/client'

export const useLocations = createGlobalState(() => {
  const locations = ref<LocationSchema[]>([])
  const error = ref<string | null>(null)

  async function fetchLocations() {
    tenantsApiListLocations()
      .then((response) => {
        if (response.data) {
          locations.value = response.data!
        }
      })
      .catch((error) => {
        console.error('Failed to fetch locations:', error)
        error.value = 'Failed to fetch locations: ' + error.message
      })
  }

  fetchLocations()

  return {
    locations,
    error,
    fetchLocations,
  }
})
