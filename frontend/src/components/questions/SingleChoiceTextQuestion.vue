<script setup lang="ts">
import { computed, type ComputedRef } from 'vue'
import { RadioButton, InputText } from 'primevue'
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
      const option = props.question.options?.find((opt) => opt.code === newChoice)

      updateAnswer([newChoice], [option?.allow_text ? '' : option?.text || ''])
    } else {
      updateAnswer([], [])
    }
    // Handled in watcher
  },
})
const text = computed<string>({
  get() {
    return answer.value.choices[0]?.text || ''
  },
  set(newText: string) {
    if (selectedChoice.value !== null) {
      const option = props.question.options?.find((opt) => opt.code === selectedChoice.value)
      updateAnswer([selectedChoice.value], [option?.allow_text ? newText : option?.text || ''])
    } else {
      updateAnswer([], [])
    }
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
  <div class="single-choice-text-question">
    <div
      v-for="option in question.options"
      :key="option.id || 0"
      class="option-item"
      :class="{ 'with-text-input': option.allow_text, active: selectedChoice === option.code }"
    >
      <RadioButton
        v-model="selectedChoice"
        :value="option.code"
        :inputId="`option-${option.id}`"
        :name="`question-${question.id}`"
      />
      <label :for="`option-${option.id}`">
        {{ option.text }}
      </label>
      <InputText
        v-if="option.allow_text && selectedChoice === option.code"
        v-model="text"
        type="text"
        :placeholder="'Additional text for ' + option.text"
        class="text-input"
      />
    </div>
  </div>
</template>
