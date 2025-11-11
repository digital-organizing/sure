import { computed, onMounted, ref } from 'vue'
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
  const answersStore = consultant === true ? consultantAnswersStore() : userAnswersStore()

  const dirty = ref(false)

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
  if (remote) {
    answer.value = {
      questionId: question.id!,
      choices: remote.choices.map((choice, idx) => ({
        code: '' + choice,
        text: remote.texts[idx] || '',
      })),
    }
  }

  // Initialize answer in store if it doesn't exist
  onMounted(() => {
    if (!answersStore.getAnswerForQuestion(question.id!)) {
      answer.value = createInitialAnswer()
    }
  })

  function updateAnswer(codes: string[], texts: string[]) {
    // Sort based on codes

    const choices = codes
      .map((code, idx) => {
        return {
          code: code,
          text: texts[idx] || '',
        }
      })
      .sort((a, b) => a.code.localeCompare(b.code))

    dirty.value = true

    answer.value = {
      questionId: question.id!,
      choices: choices,
    }
  }

  return {
    answer,
    dirty,
    updateAnswer,
    createInitialAnswer,
  }
}
