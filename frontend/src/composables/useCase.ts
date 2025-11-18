import {
  type ClientAnswerSchema,
  type InternalQuestionnaireSchema,
  sureApiGetCaseQuestionnaire,
  sureApiGetVisit,
  sureApiGetVisitClientAnswers,
  sureApiGetVisitConsultantAnswers,
  sureApiListClientCases,
  type CaseListingSchema,
  type ConsultantAnswerSchema,
  type PagedCaseListingSchema,
  sureApiGetCaseInternal,
  sureApiSubmitCase,
  type AnswerSchema,
  sureApiSubmitConsultantCase,
  sureApiUpdateCaseTags,
  type CaseHistory,
  sureApiGetVisitHistory,
  type QuestionnaireSchema,
} from '@/client'
import { computed, nextTick, ref } from 'vue'
import { createGlobalState } from '@vueuse/core'
import { consultantAnswersStore, userAnswersStore } from '@/stores/answers'

export const useCase = createGlobalState(() => {
  const visit = ref<CaseListingSchema | null>(null)
  const clientAnswers = ref<ClientAnswerSchema[] | null>(null)
  const consultantAnswers = ref<ConsultantAnswerSchema[] | null>(null)

  const store = userAnswersStore()
  const consultantStore = consultantAnswersStore()

  const consultantQuestionnaire = ref<InternalQuestionnaireSchema | null>(null)
  const clientQuestionnaire = ref<QuestionnaireSchema | null>(null)

  const pastVisits = ref<PagedCaseListingSchema | null>(null)
  const selectedVisitId = ref<string | null>(null)
  const loading = ref(false)
  const callbacks = ref<((caseId: string | null) => void)[]>([])
  const historyOffset = computed(() => {
    return Math.max(history.value.client_answers.length, history.value.consultant_answers.length)
  })

  const error = ref<string | null>(null)

  const history = ref<CaseHistory>({
    client_answers: [],
    consultant_answers: [],
  })

  async function setCaseId(visitId: string | null) {
    selectedVisitId.value = visitId
    consultantStore.setCaseId(visitId)

    history.value = {
      client_answers: [],
      consultant_answers: [],
    }
    pastVisits.value = null

    await Promise.all([
      fetchVisitDetails(),
      fetchClientAnswers(),
      fetchConsultantAnswers(),
      fetchClientSchema(),
      fetchConsultantSchema(),
      fetchPastVisits(),
      fetchCaseHistory(),
    ])

    if (visitId) {
      nextTick(() => {
        callbacks.value.forEach((callback) => callback(visitId))
        callbacks.value = []
      })
    }
  }
  const historyItems = computed(() => {
    // Merge and sort client and consultant answers by created_at
    const combined = [
      ...history.value.client_answers.map((answer) => ({
        ...answer,
        type: 'client' as const,
      })),
      ...history.value.consultant_answers.map((answer) => ({
        ...answer,
        id: `consultant-${answer.id}`,
        type: 'consultant' as const,
      })),
    ]
    combined.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    return combined
  })
  async function fetchCaseHistory(limit: number = 20, more = false) {
    if (!selectedVisitId.value) {
      error.value = 'No case ID set.'
      return
    }
    await sureApiGetVisitHistory({
      path: { pk: selectedVisitId.value },
      query: { offset: more ? historyOffset.value : 0, limit },
    })
      .then((response) => {
        if (response.data) {
          if (!more) {
            history.value = {
              client_answers: [],
              consultant_answers: [],
            }
          }
          history.value.client_answers = history.value.client_answers.concat(
            response.data.client_answers,
          )
          history.value.consultant_answers = history.value.consultant_answers.concat(
            response.data.consultant_answers,
          )
        } else {
          error.value = 'No history data in response.'
        }
      })
      .catch((error) => {
        console.error('Failed to fetch case history:', error)
      })
  }

  function onCaseId(callback: (caseId: string | null) => void) {
    if (selectedVisitId.value) {
      callback(selectedVisitId.value)
      return
    }

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
        error.value = 'Failed to fetch visit details: ' + error.message
      })
      .finally(() => {
        loading.value = false
      })
  }

  async function fetchClientSchema() {
    if (!selectedVisitId.value) {
      return
    }

    loading.value = true

    await sureApiGetCaseQuestionnaire({ path: { pk: selectedVisitId.value } })
      .then((response) => {
        if (response.data) {
          clientQuestionnaire.value = response.data!
          store.setSchema(response.data!)
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
    if (!selectedVisitId.value) {
      consultantQuestionnaire.value = null
      return
    }
    loading.value = true
    await sureApiGetCaseInternal({ path: { pk: selectedVisitId.value } })
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
    return computed(() => {
      if (!clientAnswers.value) {
        return null
      }
      const answer = clientAnswers.value.find((answer) => answer.question === questionId)
      if (!answer) {
        return null
      }
      return answer
    })
  }

  function mapAnswersForClientQuestion(questionId: number) {
    if (!visit.value || !clientAnswers.value) {
      return []
    }
    const answer = answerForClientQuestion(questionId).value
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
          store.answers.answers = response.data!.map((answer) => ({
            questionId: answer.question,
            choices: answer.choices
              ? answer.choices.map((code, idx) => ({
                  code: '' + code,
                  text: answer.texts[idx],
                }))
              : [],
          }))
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
    if (!selectedVisitId.value) {
      consultantAnswers.value = []
      return
    }

    await sureApiGetVisitConsultantAnswers({ path: { pk: selectedVisitId.value } })
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
      await sureApiListClientCases({ path: { pk: visit.value.client } })
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

  async function submitClientAnswer(answer: AnswerSchema) {
    await sureApiSubmitCase({ body: { answers: [answer] }, path: { pk: visit.value!.case } })
      .then(() => {})
      .catch((error) => {
        error.value = 'Failed to submit client answer: ' + error.message
      })
      .then(async () => {
        await Promise.all([fetchClientAnswers(), fetchCaseHistory()])
      })
  }

  async function submitConsultantAnswers(answers: AnswerSchema[]) {
    await sureApiSubmitConsultantCase({
      path: { pk: visit.value!.case },
      body: { answers: answers },
    })
      .then(() => {})
      .catch((error) => {
        error.value = 'Failed to submit consultant answers: ' + error.message
      })
      .then(async () => {
        await Promise.all([fetchConsultantAnswers(), fetchCaseHistory()])
      })
  }

  async function setCaseTags(tags: string[]) {
    await sureApiUpdateCaseTags({ path: { pk: visit.value!.case }, body: tags })
      .then(() => {})
      .catch((error) => {
        error.value = 'Failed to update case tags: ' + error.message
      })
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
    submitClientAnswer,
    submitConsultantAnswers,
    setCaseTags,
    fetchCaseHistory,
    history,
    historyItems,
  }
})
