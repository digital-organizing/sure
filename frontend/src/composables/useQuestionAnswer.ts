import { computed, onMounted } from 'vue'
import { type AnswerSchema, type ClientQuestionSchema } from '@/client'
import { userAnswersStore } from '@/stores/answers'

export function useQuestionAnswer(question: ClientQuestionSchema) {
  const answersStore = userAnswersStore()

  // Get or create answer for this question
  const answer = computed<AnswerSchema>({
    get() {
      return answersStore.getAnswerForQuestion(question.id!) || createInitialAnswer()
    },
    set(newAnswer: AnswerSchema) {
      answersStore.setAnswerForQuestion(question.id!, newAnswer.choices)
    },
  })

  function createInitialAnswer(): AnswerSchema {
    return {
      questionId: question.id!,
      choices: [],
    }
  }

  // Initialize answer in store if it doesn't exist
  onMounted(() => {
    if (!answersStore.getAnswerForQuestion(question.id!)) {
      answer.value = createInitialAnswer()
    }
  })

  function updateAnswer(codes: string[], texts: string[]) {
    const choices = codes.map((code, idx) => {
      return {
        code: code,
        text: texts[idx] || '',
      }
    })

    answer.value = {
      questionId: question.id!,
      choices: choices,
    }
  }

  return {
    answer,
    updateAnswer,
    createInitialAnswer,
  }
}
