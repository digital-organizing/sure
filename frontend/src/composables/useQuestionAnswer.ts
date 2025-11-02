import { computed, onMounted } from 'vue'
import { type ClientAnswerSchema, type ClientQuestionSchema } from '@/client'
import { userAnswersStore } from '@/stores/answers'

export function useQuestionAnswer(question: ClientQuestionSchema) {
  const answersStore = userAnswersStore()

  // Get or create answer for this question
  const answer = computed<ClientAnswerSchema>({
    get() {
      return answersStore.getAnswerForQuestion(question.id!) || createInitialAnswer()
    },
    set(newAnswer: ClientAnswerSchema) {
      answersStore.setAnswerForQuestion(question.id!, newAnswer)
    },
  })

  function createInitialAnswer(): ClientAnswerSchema {
    return {
      question: question.id!,
      choices: [],
      texts: [],
      created_at: new Date().toISOString(),
      user: null,
    }
  }

  // Initialize answer in store if it doesn't exist
  onMounted(() => {
    if (!answersStore.getAnswerForQuestion(question.id!)) {
      answer.value = createInitialAnswer()
    }
  })

  function updateAnswer(choices: number[], texts: string[]) {
    answer.value = {
      question: question.id!,
      choices,
      texts,
      created_at: new Date().toISOString(),
      user: null,
    }
  }

  return {
    answer,
    updateAnswer,
    createInitialAnswer,
  }
}
