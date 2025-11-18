<script setup lang="ts">
import { computed, type ComputedRef } from 'vue'
import { RadioButton } from 'primevue'
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
const selectedChoice = computed<string | null>({
  get() {
    return answer.value.choices[0]?.code || null
  },
  set(newChoice: string | null) {
    if (newChoice !== null) {
      const option = props.question.options?.find((opt) => opt.code == newChoice)
      updateAnswer([newChoice], [option?.text || ''])
    } else {
      updateAnswer([], [])
    }
  },
})

// Load existing answer

function getAnswer() {
  return answer.value
}

defineExpose({
  getAnswer,
})
</script>

<template>
  <div class="single-choice-question">
    <div v-for="option in question.options" :key="option.id || 0" class="option-item">
      <RadioButton
        v-model="selectedChoice"
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
