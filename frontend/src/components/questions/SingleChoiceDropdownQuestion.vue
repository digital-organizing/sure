<script setup lang="ts">
import { computed } from 'vue'
import { RadioButton, Select } from 'primevue'
import {
  type ClientAnswerSchema,
  type ClientQuestionSchema,
  type ConsultantAnswerSchema,
  type ConsultantQuestionSchema,
} from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'
import type { ComputedRef } from 'vue'

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
      let text = option?.text || ''

      // Use dropdown selection if available
      if (option?.choices && dropdownSelections.value[newChoice]) {
        text = dropdownSelections.value[newChoice]
      }

      updateAnswer([newChoice], [text])
    } else {
      updateAnswer([], [])
    }
  },
})
const dropdownSelections = computed<Record<string, string>>({
  get() {
    const selections: Record<string, string> = {}
    if (answer.value.choices && answer.value.choices.length > 0) {
      const selectedCode = answer.value.choices[0].code
      const selectedText = answer.value.choices[0].text
      const selectedOption = props.question.options?.find((opt) => opt.code === selectedCode)

      // Only return dropdown selection if it differs from the default option text
      if (selectedOption?.choices && selectedText !== selectedOption.text) {
        selections[selectedCode] = selectedText
      }
    }
    return selections
  },
  set(newSelections: Record<string, string>) {
    if (selectedChoice.value !== null) {
      const option = props.question.options?.find((opt) => opt.code == selectedChoice.value)
      let text = option?.text || ''

      // Use dropdown selection if available
      if (option?.choices && newSelections[selectedChoice.value]) {
        text = newSelections[selectedChoice.value]
      }

      updateAnswer([selectedChoice.value], [text])
    }
  },
})

function triggerDropdownUpdate() {
  // Trigger the computed setters to update the answer
  dropdownSelections.value = dropdownSelections.value
}

function getAnswer() {
  return answer.value
}

defineExpose({
  getAnswer,
})
</script>

<template>
  <div class="single-choice-dropdown-question">
    <div
      v-for="option in question.options"
      :key="option.code || 0"
      class="client-option-item"
      :class="{
        'with-text-input': option.choices && option.choices.length > 0,
        active: selectedChoice === option.code,
      }"
    >
      <RadioButton
        v-model="selectedChoice"
        :value="option.code"
        :inputId="`option-${option.code}`"
        :name="`question-${question.id}`"
      />
      <label :for="`option-${option.code}`" class="client-option-label">
        {{ option.text }}
      </label>
      <Select
        v-if="option.choices && option.choices.length && selectedChoice === option.code"
        v-model="dropdownSelections[option.code!]"
        @change="triggerDropdownUpdate"
        filter
        :options="option.choices"
        :placeholder="'Select an option'"
        class="dropdown-select"
      />
    </div>
  </div>
</template>
