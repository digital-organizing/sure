import {
  type LocationSchema,
  sureApiGetCaseStatus,
  sureApiGetClientResults,
  sureApiGetResultInfo,
  sureApiListCaseNotes,
  sureApiListDocuments,
  type DocumentSchema,
  type NoteSchema,
  type OptionSchema,
  type ResultInformationSchema,
  type TestSchema,
  tenantsApiGetLocationById,
  sureApiGetClientFreeFormResults,
  type FreeFormTestSchema,
} from '@/client'
import { createGlobalState } from '@vueuse/core'
import { ref } from 'vue'
import { useCase } from './useCase'

export const useResults = createGlobalState(() => {
  const notes = ref<NoteSchema[]>([])
  const documents = ref<DocumentSchema[]>([])
  const tests = ref<TestSchema[]>([])
  const freeFormTests = ref<FreeFormTestSchema[]>([])
  const infos = ref<ResultInformationSchema[]>([])
  const error = ref<string | null>(null)
  const caseFetched = ref(false)
  const location = ref<LocationSchema | null>(null)
  const caseStatus = ref<OptionSchema | null>(null)
  const { onCaseRefresh } = useCase()

  async function fetchCase(caseId: string, key: string, asClient = true) {
    const response = await sureApiGetCaseStatus({ path: { pk: caseId }, body: { key: key } })

    if (response.data) {
      caseStatus.value = response.data
      error.value = null
    } else if (response.error) {
      // @ts-expect-error The detail is not generated in the typing but exists in the response
      error.value = response.error['detail'] || 'An error occurred while fetching the case status.'
    }
    if (error.value) {
      console.log('Error fetching case status, aborting further data fetch.')
      return
    }

    tenantsApiGetLocationById({ path: { case_id: caseId } }).then((response) => {
      if (response.data) {
        location.value = response.data
      }
    })

    if (caseStatus.value?.value === 'not_available') {
      caseFetched.value = true
      return
    }

    if (caseStatus.value?.value == 'closed' && asClient) {
      error.value = 'Results are not available for this case anymore.'
      return
    }

    if (caseStatus.value?.value !== 'results_sent' && asClient) {
      error.value = 'Results are not yet available for this case.'
      return
    }

    await sureApiGetClientResults({
      path: { pk: caseId },
      body: { key: key },
      query: { as_client: asClient },
    })
      .then((response) => {
        if (response.data) {
          tests.value = response.data
          caseFetched.value = true
        }
      })
      .catch((err) => {
        error.value =
          err.response?.data?.detail || 'An error occurred while fetching the case results.'
      })

    sureApiGetClientFreeFormResults({ path: { pk: caseId }, body: { key: key } }).then(
      (response) => {
        if (response.data) {
          freeFormTests.value = response.data
        }
      },
    )
    sureApiListCaseNotes({ path: { pk: caseId }, body: { key: key } }).then((response) => {
      if (response.data) {
        notes.value = response.data
      }
    })
    sureApiListDocuments({ path: { pk: caseId }, body: { key: key } }).then((response) => {
      if (response.data) {
        documents.value = response.data
      }
    })
    sureApiGetResultInfo({ path: { pk: caseId }, body: { key: key } }).then((response) => {
      if (response.data) {
        infos.value = response.data
      }
    })
  }

  onCaseRefresh((caseId: string) => {
    fetchCase(caseId, '', false)
  })

  return {
    notes,
    documents,
    tests,
    infos,
    fetchCase,
    error,
    caseFetched,
    location,
    caseStatus,
    freeFormTests,
  }
})
