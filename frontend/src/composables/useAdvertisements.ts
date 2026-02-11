import { type AdvertisementSchema, tenantsApiGetAdvertisements } from '@/client'
import { createGlobalState } from '@vueuse/core'
import { computed, ref } from 'vue'
import { useTexts } from './useTexts'

export const useAdvertisement = createGlobalState(() => {
  const { language } = useTexts()
  const advertisements = ref<Array<AdvertisementSchema>>([])

  const showAdvertisements = computed(() => {
    return advertisements.value
  })

  async function fetchAdvertisements(case_id: string) {
    console.log('Fetching advertisements for case_id:', case_id, 'and language:', language.value)
    await tenantsApiGetAdvertisements({ path: { case_id }, query: { lang: language.value } }).then(
      (response) => {
        if (response.data) advertisements.value = response.data
      },
    )
  }

  return {
    advertisements,
    fetchAdvertisements,
    showAdvertisements,
  }
})
