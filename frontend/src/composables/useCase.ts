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
  sureApiGetCaseInternal,
  sureApiSubmitCase,
  type AnswerSchema,
  sureApiSubmitConsultantCase,
  sureApiUpdateCaseTags,
  type CaseHistory,
  sureApiGetVisitHistory,
  type QuestionnaireSchema,
  sureApiUpdateCaseTests,
  sureApiUpdateCaseTestResults,
  type RelatedCaseSchema,
  type TestSchema,
  sureApiGetCaseTests,
  sureApiGetCaseFreeFormTests,
  type FreeFormTestSchema,
  type DocumentSchema,
  sureApiListDocuments,
  sureApiUploadDocument,
  sureApiSetDocumentHidden,
  type NoteSchema,
  sureApiListCaseNotes,
  sureApiAddCaseNote,
  sureApiSetCaseNoteHidden,
  sureApiPublishCaseResults,
  sureApiUpdateCaseStatus,
} from '@/client'
import { computed, nextTick, ref } from 'vue'
import { createGlobalState } from '@vueuse/core'
import { consultantAnswersStore, userAnswersStore } from '@/stores/answers'
import { useTexts } from './useTexts'

export const useCase = createGlobalState(() => {
  const visit = ref<CaseListingSchema | null>(null)
  const relatedCases = ref<RelatedCaseSchema[] | null>(null)
  const clientAnswers = ref<ClientAnswerSchema[] | null>(null)
  const consultantAnswers = ref<ConsultantAnswerSchema[] | null>(null)
  const selectedTests = ref<TestSchema[]>([])
  const freeFormTests = ref<FreeFormTestSchema[]>([])
  const documents = ref<DocumentSchema[]>([])
  const notes = ref<NoteSchema[]>([])

  const { language, onLanguageChange } = useTexts()

  const store = userAnswersStore()
  const consultantStore = consultantAnswersStore()

  const consultantQuestionnaire = ref<InternalQuestionnaireSchema | null>(null)
  const clientQuestionnaire = ref<QuestionnaireSchema | null>(null)

  const selectedVisitId = ref<string | null>(null)
  const loading = ref(false)
  const callbacks = ref<((caseId: string | null) => void)[]>([])
  const refreshCallbacks = ref<((caseId: string) => void)[]>([])
  const historyOffset = computed(() => {
    return Math.max(
      history.value.client_answers.length,
      history.value.consultant_answers.length,
      history.value.tests.length,
      history.value.test_results.length,
    )
  })

  const error = ref<string | null>(null)

  const history = ref<CaseHistory>({
    client_answers: [],
    consultant_answers: [],
    tests: [],
    test_results: [],
    log: [],
  })

  async function setCaseId(visitId: string | null) {
    selectedVisitId.value = visitId
    consultantStore.setCaseId(visitId)
    refreshCallbacks.value = []

    history.value = {
      client_answers: [],
      consultant_answers: [],
      tests: [],
      test_results: [],
      log: [],
    }
    relatedCases.value = []
    selectedTests.value = []
    await fetchVisitDetails()

    await Promise.all([
      fetchClientAnswers(),
      fetchConsultantAnswers(),
      fetchClientSchema(),
      fetchConsultantSchema(),
      fetchCaseHistory(),
      fetchSelectedTests(),
      fetchDocuments(),
      fetchCaseNotes(),
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
        entry: answer,
        id: `client-${answer.id}`,
        type: 'client' as const,
      })),
      ...history.value.consultant_answers.map((answer) => ({
        entry: answer,
        id: `consultant-${answer.id}`,
        type: 'consultant' as const,
      })),
      ...history.value.tests.map((test) => ({
        entry: test,
        type: 'test' as const,
        id: `test-${test.id}`,
      })),
      ...history.value.test_results.map((result) => ({
        entry: result,
        type: 'result' as const,
        id: `result-${result.id}`,
      })),
      ...history.value.log.map((log) => ({
        entry: log,
        type: 'log' as const,
        id: `log-${log.id}`,
      })),
    ]
    combined.sort(
      (a, b) => new Date(b.entry.created_at).getTime() - new Date(a.entry.created_at).getTime(),
    )
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
              tests: [],
              test_results: [],
              log: [],
            }
          }
          history.value.client_answers = history.value.client_answers.concat(
            response.data.client_answers,
          )
          history.value.consultant_answers = history.value.consultant_answers.concat(
            response.data.consultant_answers,
          )
          history.value.tests = history.value.tests.concat(response.data.tests)
          history.value.test_results = history.value.test_results.concat(response.data.test_results)
          history.value.log = history.value.log.concat(response.data.log)
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

  function onCaseRefresh(callback: (caseId: string) => void) {
    refreshCallbacks.value.push(callback)
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
          refreshCallbacks.value.forEach((callback) => callback(visit.value!.case!))
        }
      })
      .catch((error) => {
        error.value = 'Failed to fetch visit details: ' + error.message
      })
      .finally(() => {
        loading.value = false
      })
    await fetchRelatedCases()
  }

  async function fetchClientSchema() {
    if (!selectedVisitId.value) {
      return
    }

    loading.value = true

    await sureApiGetCaseQuestionnaire({
      path: { pk: selectedVisitId.value },
      query: { lang: language.value },
    })
      .then((response) => {
        console.log(response)
        console.log('Fetched client questionnaire:', response.data)
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
    await sureApiGetCaseInternal({
      path: { pk: selectedVisitId.value },
      query: { lang: language.value },
    })
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
  async function fetchCaseNotes() {
    if (!visit.value) {
      notes.value = []
      return
    }

    fetchVisitDetails()
    await sureApiListCaseNotes({
      path: { pk: visit.value!.case },
      body: { key: '' },
      query: { as_staff: true },
    })
      .then((response) => {
        if (Array.isArray(response.data)) {
          notes.value = response.data
        }
      })
      .catch((error) => {
        console.error('Failed to fetch case notes:', error)
        error.value = 'Failed to fetch case notes: ' + error.message
      })
  }

  async function createCaseNote(content: string) {
    if (!visit.value) {
      error.value = 'No visit selected.'
      return
    }
    await sureApiAddCaseNote({ path: { pk: visit.value.case }, body: { content } })
      .catch((error) => {
        console.error('Failed to create case note:', error)
        error.value = 'Failed to create case note: ' + error.message
      })
      .then(async () => {
        await fetchCaseNotes()
      })
  }

  async function setCaseNoteHidden(id: number, hidden: boolean) {
    if (!visit.value) {
      error.value = 'No visit selected.'
      return
    }
    await sureApiSetCaseNoteHidden({
      path: { pk: visit.value.case, note_pk: id },
      body: { hidden },
    })
      .catch((error) => {
        console.error('Failed to set case note hidden:', error)
        error.value = 'Failed to set case note hidden: ' + error.message
      })
      .then(async () => {
        await fetchCaseNotes()
      })
  }

  async function fetchDocuments() {
    if (!visit.value) {
      documents.value = []
      return
    }
    fetchVisitDetails()

    await sureApiListDocuments({
      path: { pk: visit.value!.case },
      body: { key: '' },
      query: { as_staff: true },
    })
      .then((response) => {
        if (Array.isArray(response.data)) {
          documents.value = response.data
        }
      })
      .catch((error) => {
        console.error('Failed to fetch case documents:', error)
        error.value = 'Failed to fetch case documents: ' + error.message
      })
  }

  async function uploadDocument(file: File, name: string) {
    if (!visit.value) {
      error.value = 'No visit selected.'
      return
    }
    await sureApiUploadDocument({ path: { pk: visit.value.case }, body: { file, name } })
      .catch((error) => {
        console.error('Failed to upload document:', error)
        error.value = 'Failed to upload document: ' + error.message
      })
      .then(async () => {
        await fetchDocuments()
      })
  }

  async function setDocumentHidden(documentId: number, hidden: boolean) {
    if (!visit.value) {
      error.value = 'No visit selected.'
      return
    }
    await sureApiSetDocumentHidden({
      path: { pk: visit.value.case, doc_pk: documentId },
      body: { hidden },
    })
      .catch((error) => {
        console.error('Failed to set document hidden:', error)
        error.value = 'Failed to set document hidden: ' + error.message
      })
      .then(async () => {
        await fetchDocuments()
      })
  }

  async function fetchRelatedCases() {
    if (!visit.value || !visit.value.client) {
      return (relatedCases.value = [])
    }

    await sureApiListClientCases({ path: { pk: visit.value.client } })
      .then((response) => {
        if (response.data) {
          relatedCases.value = response.data.items.filter(
            (item) => item.case_id !== visit.value!.case,
          )
        }
      })
      .catch((error) => {
        console.error('Failed to fetch related cases:', error)
        error.value = 'Failed to fetch related cases: ' + error.message
      })
  }

  async function fetchSelectedTests() {
    if (!visit.value) {
      selectedTests.value = []
      freeFormTests.value = []
      return
    }
    loading.value = true
    sureApiGetCaseFreeFormTests({ path: { pk: visit.value!.case } })
      .then((response) => {
        if (Array.isArray(response.data)) {
          freeFormTests.value = response.data
        }
      })
      .catch((error) => {
        console.error('Failed to fetch case free form tests:', error)
        error.value = 'Failed to fetch case free form tests: ' + error.message
      })
    await sureApiGetCaseTests({ path: { pk: visit.value!.case } })
      .then((response) => {
        if (Array.isArray(response.data)) {
          selectedTests.value = response.data
        }
      })
      .catch((error) => {
        console.error('Failed to fetch case tests:', error)
        error.value = 'Failed to fetch case tests: ' + error.message
      })
      .finally(() => {
        loading.value = false
      })
  }

  // Assuming there's an API endpoint to fetch tests for a case

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

  async function submitClientAnswer(answer: AnswerSchema) {
    await sureApiSubmitCase({ body: { answers: [answer] }, path: { pk: visit.value!.case } })
      .then(() => {})
      .catch((error) => {
        error.value = 'Failed to submit client answer: ' + error.message
      })
      .then(async () => {
        await Promise.all([fetchVisitDetails(), fetchClientAnswers(), fetchCaseHistory()])
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
        await Promise.all([fetchVisitDetails(), fetchConsultantAnswers(), fetchCaseHistory()])
      })
  }

  async function setCaseTags(tags: string[]) {
    await sureApiUpdateCaseTags({ path: { pk: visit.value!.case }, body: tags })
      .then(() => {})
      .catch((error) => {
        error.value = 'Failed to update case tags: ' + error.message
      })
      .then(async () => {
        await fetchVisitDetails()
      })
  }

  async function updateCaseTests(testKindIds: number[], freeFormTests: string[]) {
    await sureApiUpdateCaseTests({
      path: { pk: visit.value!.case },
      body: { free_form_tests: freeFormTests, test_kind_ids: testKindIds },
    })
      .then(() => {})
      .catch((error) => {
        error.value = 'Failed to update case tests: ' + error.message
      })
      .then(async () => {
        await Promise.all([fetchVisitDetails(), fetchSelectedTests(), fetchCaseHistory()])
      })
  }

  async function updateCaseTestResults(
    results: { [nr: string]: string | null },
    notes: { [nr: string]: string | null },
    freeFormResults: { [id: string]: string },
  ) {
    if (!visit.value) {
      error.value = 'No visit selected.'
      return
    }
    const testResults = Object.entries(results).map((entry) => {
      return {
        number: Number(entry[0]),
        label: entry[1]!,
        note: notes[Number(entry[0])] || '',
      }
    })
    const freeFormResultsEntries = Object.entries(freeFormResults).map((entry) => {
      return {
        id: +entry[0],
        result: entry[1],
      }
    })
    await sureApiUpdateCaseTestResults({
      path: { pk: visit.value.case },
      body: { test_results: testResults, free_form_results: freeFormResultsEntries },
    })
      .then(() => {})
      .catch((error) => {
        error.value = 'Failed to update case test results: ' + error.message
      })
      .then(async () => {
        await Promise.all([fetchVisitDetails(), fetchSelectedTests(), fetchCaseHistory()])
      })
  }

  async function publishResults() {
    await sureApiPublishCaseResults({ path: { pk: visit.value!.case } })
      .then(() => {
        // Successfully published results
      })
      .catch((error) => {
        error.value = 'Failed to publish case results: ' + error.message
      })
    await Promise.all([fetchVisitDetails(), fetchCaseHistory()])
  }

  async function setCaseStatus(status: string) {
    await sureApiUpdateCaseStatus({ path: { pk: visit.value!.case }, query: { status } })
    await Promise.all([fetchVisitDetails(), fetchCaseHistory()])
  }

  onLanguageChange(async () => {
    if (selectedVisitId.value) {
      await fetchClientSchema()
      await fetchConsultantSchema()
    }
  })

  return {
    visit,
    error,
    loading,
    clientAnswers,
    consultantAnswers,
    consultantQuestionnaire,
    clientQuestionnaire,
    setCaseId,
    fetchVisitDetails,
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
    updateCaseTests,
    updateCaseTestResults,
    fetchCaseHistory,
    fetchDocuments,
    uploadDocument,
    setDocumentHidden,
    setCaseNoteHidden,
    fetchCaseNotes,
    createCaseNote,
    notes,
    documents,
    relatedCases,
    selectedTests,
    freeFormTests,
    history,
    historyItems,
    setCaseStatus,
    publishResults,
    onCaseRefresh,
  }
})
