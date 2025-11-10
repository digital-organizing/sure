import { computed, onMounted } from 'vue'
import {
  type AnswerSchema,
  type ClientAnswerSchema,
  type ClientQuestionSchema,
  type ConsultantAnswerSchema,
  type ConsultantQuestionSchema,
} from '@/client'
import { consultantAnswersStore, userAnswersStore } from '@/stores/answers'

export function useQuestionAnswer(
  question: ClientQuestionSchema | ConsultantQuestionSchema,
  remote: ClientAnswerSchema | ConsultantAnswerSchema | null | undefined = undefined,
  consultant: boolean = false,
) {
  const answersStore = consultant ? userAnswersStore() : consultantAnswersStore()

  // Get or create answer for this question
  const answer = computed<AnswerSchema>({
    get() {
      if (remote === undefined) {
        return answersStore.getAnswerForQuestion(question.id!) || createInitialAnswer()
      }

      if (remote === null) {
        return createInitialAnswer()
      }
      return {
        questionId: question.id!,
        choices: remote.choices.map((choice, idx) => {
          return {
            code: '' + choice,
            text: remote.texts[idx] || '',
          }
        }),
      }
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
