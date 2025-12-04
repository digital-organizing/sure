import { tenantsApiListTags, type TagSchema } from '@/client'
import { createGlobalState } from '@vueuse/core'
import { ref } from 'vue'

export const useTags = createGlobalState(() => {
  const tags = ref<TagSchema[]>([])
  const error = ref<string | null>(null)

  function fetchTags() {
    tenantsApiListTags()
      .then((response) => {
        if (response.data) {
          tags.value = response.data!
        }
      })
      .catch((error) => {
        console.error('Failed to fetch tags:', error)
      })
  }

  fetchTags()

  return {
    tags,
    error,
    fetchTags,
  }
})
