<script setup lang="ts">
import { computed, type ComputedRef } from 'vue'
import { Checkbox } from 'primevue'
import {
  type ClientAnswerSchema,
  type ClientQuestionSchema,
  type ConsultantAnswerSchema,
  type ConsultantQuestionSchema,
  type ClientOptionSchema,
  type ConsultantOptionSchema,
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

const isOptionDisabled = (option: ClientOptionSchema | ConsultantOptionSchema) => {
  const selectedOpts = props.question.options?.filter((opt) => selectedChoices.value.includes(opt.code!)) || []
  const hasSelectedExclusive = selectedOpts.some((opt) => opt.exclusive)
  const hasSelectedNonExclusive = selectedOpts.some((opt) => !opt.exclusive)

  if (hasSelectedExclusive) {
    return !selectedChoices.value.includes(option.code!)
  }
  if (hasSelectedNonExclusive) {
    return !!option.exclusive
  }
  return false
}

function getAnswer() {
  return answer.value
}

defineExpose({
  getAnswer,
})
</script>

<template>
  <div class="multiple-choice-question">
    <div
      v-for="option in question.options"
      :key="option.id || 0"
      class="client-option-item"
      :class="{ disabled: isOptionDisabled(option) }"
    >
      <Checkbox
        v-model="selectedChoices"
        :value="option.code"
        :inputId="`option-${option.id}`"
        :name="`question-${question.id}`"
        :disabled="isOptionDisabled(option)"
      />
      <label :for="`option-${option.id}`" class="client-option-label">
        {{ option.text }}
      </label>
    </div>
  </div>
</template>
