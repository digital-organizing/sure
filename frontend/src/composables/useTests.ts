import { sureApiListTests, type TestCategorySchema } from '@/client'
import { createGlobalState } from '@vueuse/core'
import { computed, ref } from 'vue'

import { useTexts } from './useTexts'

export const useTests = createGlobalState(() => {
  const testCategories = ref<TestCategorySchema[]>([])
  const error = ref<string | null>(null)

  const { onLanguageChange, language } = useTexts()

  const testBundles = computed(() => {
    return testCategories.value
      .flatMap((category) => category.test_kinds.flatMap((test) => test.test_bundles))
      .filter((value, index, self) => self.findIndex((v) => v.id === value.id) === index)
      .sort((a, b) => a.name.localeCompare(b.name))
  })

  const testKinds = computed(() => {
    return testCategories.value.flatMap((category) => category.test_kinds)
  })

  async function fetchTestCategories() {
    await sureApiListTests({ query: { lang: language.value } }).then((response) => {
      if (response.data) testCategories.value = response.data
      else error.value = 'Failed to fetch test categories.'
    })
  }

  onLanguageChange(() => {
    fetchTestCategories()
  })

  fetchTestCategories()

  return {
    fetchTestCategories,
    testKinds,
    testBundles,
    testCategories,
    error,
  }
})
