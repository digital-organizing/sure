import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ClientAnswerSchema } from '@/client'

export const userAnswersStore = defineStore('answers', () => {
  const sections = ref<Map<number, Array<ClientAnswerSchema>>>(new Map())
  const schema = ref<ClientAnswerSchema | null>(null)
  const answers = ref<Map<number, ClientAnswerSchema>>(new Map())

  const getAnswerForQuestion = (questionId: number) => {
    return answers.value.get(questionId) || null
  }

  const setAnswerForQuestion = (questionId: number, answer: ClientAnswerSchema) => {
    answers.value.set(questionId, answer)
    saveAnswers()
  }

  const saveAnswers = () => {
    localStorage.setItem('userAnswers', JSON.stringify(Array.from(answers.value.entries())))
  }

  const loadAnswers = () => {
    const stored = localStorage.getItem('userAnswers')
    if (stored) {
      const parsed: Array<[number, ClientAnswerSchema]> = JSON.parse(stored)
      answers.value = new Map(parsed)
    }
  }

  const getAnswersForSection = (sectionId: number) => {
    return sections.value.get(sectionId) || []
  }

  const setAnswersForSection = (sectionId: number, answers: Array<ClientAnswerSchema>) => {
    sections.value.set(sectionId, answers)
  }
  loadAnswers()

  return {
    sections,
    schema,
    answers,
    getAnswersForSection,
    setAnswersForSection,
    getAnswerForQuestion,
    setAnswerForQuestion,
  }
})
