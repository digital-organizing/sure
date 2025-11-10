import {
  type ClientAnswerSchema,
  type InternalQuestionnaireSchema,
  type QuestionnaireSchema,
  sureApiGetCaseQuestionnaire,
  sureApiGetVisit,
  sureApiGetVisitClientAnswers,
  sureApiGetVisitConsultantAnswers,
  sureApiListClientCases,
  type CaseListingSchema,
  type ConsultantAnswerSchema,
  type PagedCaseListingSchema,
  sureApiGetCaseInternal,
} from '@/client'
import { nextTick, ref } from 'vue'
import { createGlobalState } from '@vueuse/core'

export const useCase = createGlobalState(() => {
  const visit = ref<CaseListingSchema | null>(null)
  const clientAnswers = ref<ClientAnswerSchema[]>([])
  const consultantAnswers = ref<ConsultantAnswerSchema[]>([])

  const clientQuestionnaire = ref<QuestionnaireSchema | null>(null)
  const consultantQuestionnaire = ref<InternalQuestionnaireSchema | null>(null)

  const pastVisits = ref<PagedCaseListingSchema | null>(null)
  const selectedVisitId = ref<string | null>(null)
  const loading = ref(false)
  const callbacks = ref<((caseId: string | null) => void)[]>([])

  const error = ref<string | null>(null)

  async function setCaseId(visitId: string | null) {
    selectedVisitId.value = visitId

    pastVisits.value = null
    await fetchVisitDetails()
    if (visitId) {
      nextTick(() => {
        callbacks.value.forEach((callback) => callback(visitId))
        callbacks.value = []
      })
    }
  }

  function onCaseId(callback: (caseId: string | null) => void) {
    if (selectedVisitId.value) {
      console.log('onCaseId immediate callback with:', selectedVisitId.value)
      callback(selectedVisitId.value)
      return
    }

    console.log('onCaseId registering callback')

    callbacks.value.push(callback)
  }

  async function fetchVisitDetails() {
    if (!selectedVisitId.value) {
      visit.value = null
      return
    }
    loading.value = true
    await sureApiGetVisit({ path: { pk: selectedVisitId.value! } })
      .then((response) => {
        if (response.data) {
          visit.value = response.data!
        }
      })
      .catch((error) => {
        console.error('Failed to fetch visit details:', error)
        error.value = 'Failed to fetch visit details: ' + error.message
      })
      .finally(() => {
        loading.value = false
      })
  }

  async function fetchClientSchema() {
    console.log('fetchClientSchema called', visit.value)
    if (!visit.value) {
      clientQuestionnaire.value = null
      return
    }
    console.log('fetchClientSchema fetching for case:', visit.value.case)

    loading.value = true

    await sureApiGetCaseQuestionnaire({ path: { pk: visit.value.case } })
      .then((response) => {
        if (response.data) {
          clientQuestionnaire.value = response.data!
        }
      })
      .catch((error) => {
        console.error('Failed to fetch client questionnaire:', error)
        error.value = 'Failed to fetch client questionnaire: ' + error.message
      })
      .finally(() => {
        loading.value = false
      })
  }

  async function fetchConsultantSchema() {
    if (!visit.value) {
      consultantQuestionnaire.value = null
      return
    }
    loading.value = true
    await sureApiGetCaseInternal({ path: { pk: visit.value.case } })
      .then((response) => {
        if (response.data) {
          consultantQuestionnaire.value = response.data!
        }
      })
      .catch((error) => {
        console.error('Failed to fetch consultant questionnaire:', error)
        error.value = 'Failed to fetch consultant questionnaire: ' + error.message
      })
      .finally(() => {
        loading.value = false
      })
  }

  function answerForClientQuestion(questionId: number) {
    if (!visit.value || !clientAnswers.value) {
      return null
    }
    const answer = clientAnswers.value.find((answer) => answer.question === questionId)
    if (!answer) {
      return null
    }

    return answer
  }

  function mapAnswersForClientQuestion(questionId: number) {
    if (!visit.value || !clientAnswers.value) {
      return []
    }
    const answer = answerForClientQuestion(questionId)
    if (!answer) {
      return []
    }

    return answer.texts.map((text, idx) => {
      return {
        text: text,
        created_at: answer.created_at,
        user: answer.user,
        index: idx,
        id: `${answer.question}-${idx}`,
        code: answer.choices ? answer.choices[idx] : null,
      }
    })
  }

  function answerForConsultantQuestion(questionId: number) {
    if (!visit.value || !consultantAnswers.value) {
      return null
    }
    const answer = consultantAnswers.value.find((answer) => answer.question === questionId)

    return answer
  }

  function mapAnswersForConsultantQuestion(questionId: number) {
    if (!visit.value || !consultantAnswers.value) {
      return []
    }
    const answer = answerForConsultantQuestion(questionId)

    if (!answer) {
      return []
    }

    return answer.texts.map((text, idx) => {
      return {
        text: text,
        created_at: answer.created_at,
        user: answer.user,
        index: idx,
        id: `${answer.question}-${idx}`,
        code: answer.choices ? answer.choices[idx] : null,
      }
    })
  }

  async function fetchClientAnswers() {
    if (!visit.value) {
      clientAnswers.value = []
      return
    }

    loading.value = true

    await sureApiGetVisitClientAnswers({ path: { pk: visit.value.case } })
      .then((response) => {
        if (response.data) {
          clientAnswers.value = response.data!
        }
      })
      .catch((error) => {
        console.error('Failed to fetch client answers:', error)
        error.value = 'Failed to fetch client answers: ' + error.message
      })
      .finally(() => {
        loading.value = false
      })
  }

  async function fetchConsultantAnswers() {
    if (!visit.value) {
      consultantAnswers.value = []
      return
    }

    await sureApiGetVisitConsultantAnswers({ path: { pk: visit.value.case } })
      .then((response) => {
        if (response.data) {
          consultantAnswers.value = response.data!
        }
      })
      .catch((error) => {
        console.error('Failed to fetch consultant answers:', error)
        error.value = 'Failed to fetch consultant answers: ' + error.message
      })
  }

  async function fetchPastVisits() {
    if (visit.value && visit.value.client) {
      await sureApiListClientCases({ path: { id: visit.value.client } })
        .then((response) => {
          if (response.data) {
            pastVisits.value = response.data!
          }
        })
        .catch((error) => {
          console.error('Failed to fetch client cases:', error)
          error.value = 'Failed to fetch client cases: ' + error.message
        })
    }
  }

  return {
    visit,
    error,
    loading,
    clientAnswers,
    consultantAnswers,
    consultantQuestionnaire,
    clientQuestionnaire,
    pastVisits,
    setCaseId,
    fetchVisitDetails,
    fetchPastVisits,
    fetchClientAnswers,
    fetchConsultantAnswers,
    fetchClientSchema,
    fetchConsultantSchema,
    mapAnswersForClientQuestion,
    mapAnswersForConsultantQuestion,
    answerForClientQuestion,
    answerForConsultantQuestion,
    onCaseId,
  }
})
