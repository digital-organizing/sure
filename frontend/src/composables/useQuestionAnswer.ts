import { computed, ref, type Ref } from 'vue'
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
  remote: Ref<ClientAnswerSchema | ConsultantAnswerSchema | null> | null = null,
  consultant: boolean = false,
) {
  const answersStore = consultant === true ? consultantAnswersStore() : userAnswersStore()

  const remoteRef = remote !== null ? remote : ref(null)

  const dirty = ref(false)

  // Get or create answer for this question
  const answer = computed<AnswerSchema>({
    get() {
      if (!dirty.value && remoteRef.value) {
        return createInitialAnswer()
      }
      return answersStore.getAnswerForQuestion(question.id!) || createInitialAnswer()
    },
    set(newAnswer: AnswerSchema) {
      answersStore.setAnswerForQuestion(question.id!, newAnswer.choices)
    },
  })

  function createInitialAnswer(): AnswerSchema {
    if (remoteRef.value) {
      return {
        questionId: question.id!,
        choices: remoteRef.value.choices.map((choice, idx) => ({
          code: '' + choice,
          text: remoteRef.value!.texts[idx] || '',
        })),
      }
    }
    return {
      questionId: question.id!,
      choices: [],
    }
  }

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
