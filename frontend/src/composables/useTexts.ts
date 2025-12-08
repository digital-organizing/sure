import { textsApiListLanguages, textsApiListTexts } from '@/client'
import { createGlobalState, usePreferredLanguages } from '@vueuse/core'
import { computed, readonly, ref } from 'vue'
import MarkdownIt from 'markdown-it'

export const useTexts = createGlobalState(() => {
  const texts = ref<Record<string, string>>({})
  const availableLanguages = ref<[string, string][]>([])

  const md = new MarkdownIt({
    linkify: true,
    html: true,
    breaks: true,
    typographer: true,
  })

  const loadingAvailableLanguagesPromise = ref<Promise<void> | null>(null)
  const loadingPromise = ref<Promise<void> | null>(null)

  const language = ref<string | null>(null)
  const rightToLeft = ref<boolean>(false)

  const languages = usePreferredLanguages()

  async function loadAvailableLanguages() {
    loadingAvailableLanguagesPromise.value = textsApiListLanguages().then((response) => {
      if (!response.data) return
      availableLanguages.value = response.data
    })
    await loadingAvailableLanguagesPromise.value
  }

  loadAvailableLanguages().then(() => {
    const storedLang = localStorage.getItem('preferredLanguage')
    if (storedLang) {
      setLanguage(storedLang)
      return
    }
    const preferredLang = languages.value.find((lang) =>
      availableLanguages.value.find(([code, _]) => code === lang),
    )
    setLanguage(preferredLang || 'en')
  })

  async function setLanguage(lang?: string) {
    if (!lang) {
      lang = localStorage.getItem('preferredLanguage') || 'en'
    }
    if (language.value === lang) return
    if (loadingAvailableLanguagesPromise.value) {
      await loadingAvailableLanguagesPromise.value
    }
    if (loadingPromise.value) {
      await loadingPromise.value
      if (language.value === lang) return
    }
    if (!availableLanguages.value.find(([code, _]) => code === lang)) {
      console.warn(`Language ${lang} is not available.`)
      return
    }
    localStorage.setItem('preferredLanguage', lang)
    loadingPromise.value = textsApiListTexts({ query: { lang } }).then((response) => {
      if (!response.data) return
      texts.value = response.data.texts
      rightToLeft.value = response.data.right_to_left
      language.value = response.data.language!
    })

    await loadingPromise.value
    callbacks.forEach((callback) => callback(language.value))
  }

  async function getLanguage() {
    return language.value
  }

  function render(slug: string) {
    return md.renderInline(texts.value[slug] || slug)
  }

  function getText(slug: string) {
    if (language.value === null) {
      setLanguage()
    }
    return computed(() => {
      return texts.value[slug] || slug
    })
  }

  function formatText(slug: string, args: Record<string, string>[], markdown = false) {
    if (language.value === null) {
      setLanguage()
    }
    return computed(() => {
      if (!texts.value[slug]) return slug

      let text = texts.value[slug]
      args.forEach(({ key, value }) => {
        const regex = new RegExp(`{${key}}`, 'g')
        text = text.replace(regex, value)
      })
      if (markdown) {
        text = md.renderInline(text)
      }
      return text
    })
  }

  async function getAvailableLanguages() {
    if (loadingAvailableLanguagesPromise.value) {
      await loadingAvailableLanguagesPromise.value
    }
    return availableLanguages.value
  }

  async function isRightToLeft() {
    if (loadingPromise.value) {
      await loadingPromise.value
    }
    return rightToLeft.value
  }

  const callbacks: ((lang: string | null) => void)[] = []

  function onLanguageChange(callback: (lang: string | null) => void) {
    callbacks.push(callback)
  }

  return {
    texts,
    setLanguage,
    getLanguage,
    getText,
    getAvailableLanguages,
    isRightToLeft,
    formatText,
    language: readonly(language),
    onLanguageChange,
    render,
  }
})
