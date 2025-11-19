<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RadioButton, InputText, Textarea } from 'primevue'
import { type ClientQuestionSchema } from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'

const props = defineProps<{
  question: ClientQuestionSchema
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question)
const selectedChoice = ref<string | null>(null)
const textInputs = ref<Record<string, string>>({})
const isConsultWish = computed(() => props.question.code === 'CONSULT-WISH')

// Load existing answer
if (answer.value.choices && answer.value.choices.length > 0) {
  selectedChoice.value = answer.value.choices[0].code

  // Load text inputs if they exist
  if (answer.value.choices && answer.value.choices.length > 0) {
    const selectedOption = props.question.options?.find((opt) => opt.code === selectedChoice.value)
    if (selectedOption?.allow_text) {
      textInputs.value[selectedChoice.value] = answer.value.choices[0].text
    }
  }
}

// Update store when selection or text changes
watch(
  [selectedChoice, textInputs],
  () => {
    if (selectedChoice.value !== null) {
      const option = props.question.options?.find((opt) => opt.code === selectedChoice.value)
      let text = option?.text || ''

      // Use custom text if option allows it and text is provided
      if (option?.allow_text && textInputs.value[selectedChoice.value]) {
        text = textInputs.value[selectedChoice.value]
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
  <div class="single-choice-text-question">
    <div
      v-for="option in question.options"
      :key="option.id || 0"
      class="client-option-item"
      :class="{ 'with-text-input': option.allow_text, active: selectedChoice === option.code }"
    >
      <RadioButton
        v-model="selectedChoice"
        :value="option.code"
        :inputId="`option-${option.id}`"
        :name="`question-${question.id}`"
      />
      <label :for="`option-${option.id}`" class="client-option-label">
        {{ option.text }}
      </label>
      <template v-if="option.allow_text && selectedChoice === option.code">
        <Textarea
          v-if="isConsultWish"
          v-model="textInputs[option.code]"
          autoResize
          :rows="4"
          :placeholder="'Additional text for ' + option.text"
          class="text-input consult-wish-textarea"
        />
        <InputText
          v-else
          v-model="textInputs[option.code]"
          type="text"
          :placeholder="'Additional text for ' + option.text"
          class="text-input"
        />
      </template>
    </div>
  </div>
</template>

<style scoped>
.consult-wish-textarea {
  min-height: 120px;
}
</style>
