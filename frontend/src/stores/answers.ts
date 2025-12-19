import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import {
  type SubmitCaseSchema,
  type ChoiceSchema,
  type ClientAnswerSchema,
  type QuestionnaireSchema,
  type AnswerSchema,
} from '@/client'

export const userAnswersStore = defineStore('answers', () => {
  const sections = ref<Map<number, Array<ClientAnswerSchema>>>(new Map())
  const schema = ref<QuestionnaireSchema | null>(null)
  const answers = ref<SubmitCaseSchema>({ answers: [] })

  const optionToQuestion = ref<Map<number, [number, string]>>(new Map())

  const getAnswerForQuestion = (questionId: number) => {
    return answers.value.answers.find((answer) => answer.questionId === questionId) || null
  }

  const setSchema = (newSchema: QuestionnaireSchema) => {
    schema.value = newSchema
    optionToQuestion.value = new Map()
    newSchema.sections.forEach((section) => {
      section.client_questions.forEach((question) => {
        question.options.forEach((option) => {
          optionToQuestion.value.set(option.id!, [question.id!, option.code])
        })
      })
    })
  }

  const setAnswerForQuestion = (questionId: number, choices: ChoiceSchema[]) => {
    const answer = { questionId, choices }
    // Remove existing answer if any
    answers.value.answers = answers.value.answers.filter((a) => a.questionId !== questionId)
    // Add new answer
    answers.value.answers.push(answer)
    saveAnswers()
  }

  const isOptionSelected = (optionId: number) => {
    const option = optionToQuestion.value.get(optionId)
    if (!option) return false
    const [questionId, optionCode] = option

    const answer = getAnswerForQuestion(questionId)
    if (!answer) return false

    const selected = answer.choices.some((choice) => choice.code === optionCode)
    if (selected) return true
  }

  const saveAnswers = () => {
    // localStorage.setItem('userAnswers', JSON.stringify(answers.value))
  }

  const loadAnswers = () => {
    // const stored = localStorage.getItem('userAnswers')
    const stored = null
    if (stored) {
      const parsed = JSON.parse(stored)
      if (parsed && Array.isArray(parsed.answers)) {
        answers.value = parsed
      }
    }
  }

  const getAnswersForSection = (sectionId: number) => {
    return sections.value.get(sectionId) || []
  }

  const setAnswersForSection = (sectionId: number, answers: Array<ClientAnswerSchema>) => {
    sections.value.set(sectionId, answers)
  }

  const clearAnswers = () => {
    answers.value = { answers: [] }
    saveAnswers()
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
    isOptionSelected,
    setSchema,
    clearAnswers,
  }
})

export const consultantAnswersStore = defineStore('consultant-answers', () => {
  const answers = ref<AnswerSchema[]>([])
  const caseId = ref<string | null>(null)

  function setCaseId(newCaseId: string | null) {
    if (newCaseId) caseId.value = newCaseId
  }

  function clearAnswers() {
    answers.value = []
    saveAnswers()
  }

  function getAnswerForQuestion(questionId: number) {
    return answers.value.find((answer) => answer.questionId === questionId) || null
  }

  function setAnswerForQuestion(questionId: number, choices: ChoiceSchema[]) {
    answers.value = answers.value.filter((a) => a.questionId !== questionId)
    answers.value.push({ questionId, choices })
    saveAnswers()
  }

  function saveAnswers() {
    localStorage.setItem(
      'consultantAnswers',
      JSON.stringify({
        answers: answers.value,
        caseId: caseId.value,
      }),
    )
  }

  function loadAnswers() {
    const stored = localStorage.getItem('consultantAnswers')
    if (stored) {
      const parsed = JSON.parse(stored)
      if (parsed && Array.isArray(parsed.answers)) {
        answers.value = parsed.answers
        caseId.value = parsed.caseId || null
      }
    }
  }
  loadAnswers()

  watch(caseId, (newId, oldId) => {
    if (newId !== oldId) clearAnswers()
  })

  return {
    answers,
    caseId,
    getAnswerForQuestion,
    setAnswerForQuestion,
    clearAnswers,
    setCaseId,
  }
})
