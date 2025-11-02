import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ClientAnswerSchema } from '@/client'

export const userAnswersStore = defineStore('answers', () => {
  const sections = ref<Map<number, Array<ClientAnswerSchema>>>(new Map())

  const getAnswersForSection = (sectionId: number) => {
    return sections.value.get(sectionId) || []
  }

  const setAnswersForSection = (sectionId: number, answers: Array<ClientAnswerSchema>) => {
    sections.value.set(sectionId, answers)
  }

  return {
    sections,
    getAnswersForSection,
    setAnswersForSection,
  }
})
    