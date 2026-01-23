import { type BannerSchema, tenantsApiGetBanners } from '@/client'
import { createGlobalState } from '@vueuse/core'
import { computed, ref } from 'vue'
import { useTexts } from './useTexts'

export const useBanner = createGlobalState(() => {
  const { language, onLanguageChange } = useTexts()
  const banners = ref<Array<BannerSchema>>([])
  const dismissed = ref<Array<number>>([])

  const loadDismissed = () => {
    try {
      const dismissedBanners = localStorage.getItem('dismissedBanners')
      if (dismissedBanners) {
        dismissed.value = JSON.parse(dismissedBanners)
      }
    } catch (e) {
      console.error('Failed to load dismissed banners from localStorage:', e)
    }
  }
  const saveDismissed = () => {
    try {
      localStorage.setItem('dismissedBanners', JSON.stringify(dismissed.value))
    } catch (e) {
      console.error('Failed to save dismissed banners to localStorage:', e)
    }
  }

  loadDismissed()

  const showBanners = computed(() => {
    return banners.value.filter((banner) => !dismissed.value.includes(banner.id!))
  })

  async function fetchBanners() {
    await tenantsApiGetBanners({ query: { lang: language.value } }).then((response) => {
      if (response.data) banners.value = response.data
    })
  }

  function dismissBanner(bannerId: number) {
    if (!dismissed.value.includes(bannerId)) {
      dismissed.value.push(bannerId)
      saveDismissed()
    }
  }

  onLanguageChange(() => {
    fetchBanners()
  })

  fetchBanners()

  return {
    banners,
    fetchBanners,
    dismissed,
    showBanners,
    dismissBanner,
  }
})
