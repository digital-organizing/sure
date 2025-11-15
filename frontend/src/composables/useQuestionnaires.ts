import { type QuestionnaireListingSchema, sureApiListQuestionnaires } from '@/client'
import { ref } from 'vue'

export const useQuestionnaires = () => {
  const questionnaires = ref<QuestionnaireListingSchema[]>([])
  const error = ref<string | null>(null)

  async function fetchQuestionnaires() {
    try {
      const response = await sureApiListQuestionnaires()
      if (response.data) {
        questionnaires.value = response.data
      }
    } catch (err) {
      console.error('Failed to fetch questionnaires:', err)
      error.value = 'Failed to fetch questionnaires'
    }
  }

  fetchQuestionnaires()

  return {
    questionnaires,
    error,
    fetchQuestionnaires,
  }
}
