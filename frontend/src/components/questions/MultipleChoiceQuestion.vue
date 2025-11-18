<script setup lang="ts">
import { computed, type ComputedRef } from 'vue'
import { Checkbox } from 'primevue'
import {
  type ClientAnswerSchema,
  type ClientQuestionSchema,
  type ConsultantAnswerSchema,
  type ConsultantQuestionSchema,
} from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'

const props = defineProps<{
  question: ClientQuestionSchema | ConsultantQuestionSchema
  remote?: ComputedRef<ClientAnswerSchema | ConsultantAnswerSchema | null>
  consultant?: boolean
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question, props.remote, props.consultant)
const selectedChoices = computed<string[]>({
  get() {
    return [...answer.value.choices.map((choice) => choice.code)]
  },
  set(newChoices: string[]) {
    const texts = newChoices.map((choiceId) => {
      const option = props.question.options?.find((opt) => opt.code === choiceId)
      return option?.text || ''
    })
    updateAnswer(newChoices, texts)
  },
})

function getAnswer() {
  return answer.value
}

defineExpose({
  getAnswer,
})
</script>

<template>
  <div class="multiple-choice-question">
    <div v-for="option in question.options" :key="option.id || 0" class="option-item">
      <Checkbox
        v-model="selectedChoices"
        :value="option.code"
        :inputId="`option-${option.id}`"
        :name="`question-${question.id}`"
      />
      <label :for="`option-${option.id}`" class="option-label">
        {{ option.text }}
      </label>
    </div>
  </div>
</template>
