<script setup lang="ts">
import { ref, watch } from 'vue'
import { RadioButton, Select } from 'primevue'
import { type ClientQuestionSchema } from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'

const props = defineProps<{
  question: ClientQuestionSchema
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question)
const selectedChoice = ref<string | null>(null)
const dropdownSelections = ref<Record<string, string>>({})

// Load existing answer
if (answer.value.choices && answer.value.choices.length > 0) {
  selectedChoice.value = answer.value.choices[0].code

  // Load dropdown selection if it exists
  if (answer.value.choices && answer.value.choices.length > 0) {
    const selectedOption = props.question.options?.find((opt) => opt.code === selectedChoice.value)
    const text = answer.value.choices[0].text

    // Check if this is a dropdown selection (not the default option text)
    if (selectedOption?.choices && text !== selectedOption.text) {
      dropdownSelections.value[selectedChoice.value] = text
    }
  }
}

// Update store when selection changes
watch(
  [selectedChoice, dropdownSelections],
  () => {
    if (selectedChoice.value !== null) {
      const option = props.question.options?.find((opt) => opt.id === selectedChoice.value)
      let text = option?.text || ''

      // Use dropdown selection if available
      if (option?.choices && dropdownSelections.value[selectedChoice.value]) {
        text = dropdownSelections.value[selectedChoice.value]
      }

      updateAnswer([selectedChoice.value], [text])
    } else {
      updateAnswer([], [])
    }
  },
  { deep: true },
)

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
      class="option-item"
      :class="{
        'with-dropdown': option.choices && option.choices.length > 0,
        active: selectedChoice === option.code,
      }"
    >
      <RadioButton
        v-model="selectedChoice"
        :value="option.code"
        :inputId="`option-${option.code}`"
        :name="`question-${question.id}`"
      />
      <label :for="`option-${option.code}`">
        {{ option.text }}
      </label>
      <Select
        v-if="option.choices && option.choices.length && selectedChoice === option.code"
        v-model="dropdownSelections[option.code!]"
        filter
        :options="option.choices"
        :placeholder="'Select an option for ' + option.text"
        class="dropdown-select"
      />
    </div>
  </div>
</template>

<style scoped>
.option-item {
  margin-bottom: 0.75rem;
}
.option-item label {
  margin-left: 0.75rem;
}
</style>
