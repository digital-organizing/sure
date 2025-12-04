import { type BannerSchema, tenantsApiGetBanners } from '@/client'
import { createGlobalState } from '@vueuse/core'
import { computed, ref } from 'vue'

export const useBanner = createGlobalState(() => {
  const banners = ref<Array<BannerSchema>>([])
  const dismissed = ref<Array<number>>([])

  const loadDismissed = () => {
    const dismissedBanners = localStorage.getItem('dismissedBanners')
    if (dismissedBanners) {
      dismissed.value = JSON.parse(dismissedBanners)
    }
  }
  const saveDismissed = () => {
    localStorage.setItem('dismissedBanners', JSON.stringify(dismissed.value))
  }

  loadDismissed()

  const showBanners = computed(() => {
    return banners.value.filter((banner) => !dismissed.value.includes(banner.id!))
  })

  async function fetchBanners() {
    await tenantsApiGetBanners().then((response) => {
      if (response.data) banners.value = response.data
    })
  }

  function dismissBanner(bannerId: number) {
    if (!dismissed.value.includes(bannerId)) {
      dismissed.value.push(bannerId)
      saveDismissed()
    }
  }

  fetchBanners()

  return {
    banners,
    fetchBanners,
    dismissed,
    showBanners,
    dismissBanner,
  }
})
