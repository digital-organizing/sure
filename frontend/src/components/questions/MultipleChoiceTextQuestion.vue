<script setup lang="ts">
import { ref, watch } from 'vue'
import { Checkbox, InputText } from 'primevue'
import { type ClientQuestionSchema } from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'

const props = defineProps<{
  question: ClientQuestionSchema
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question)
const selectedChoices = ref<number[]>([])
const textInputs = ref<Record<number, string>>({})

// Load existing answer
if (answer.value.choices && answer.value.choices.length > 0) {
  selectedChoices.value = [...(answer.value.choices as number[])]

  // Load text inputs if they exist
  if (answer.value.texts && answer.value.texts.length > 0) {
    selectedChoices.value.forEach((choiceId, index) => {
      const option = props.question.options?.find((opt) => opt.id === choiceId)
      if (option?.allow_text && answer.value.texts![index]) {
        textInputs.value[choiceId] = answer.value.texts![index] as string
      }
    })
  }
}

// Update store when selection or text changes
watch(
  [selectedChoices, textInputs],
  () => {
    const texts = selectedChoices.value.map((choiceId) => {
      const option = props.question.options?.find((opt) => opt.id === choiceId)

      // Use custom text if option allows it and text is provided
      if (option?.allow_text && textInputs.value[choiceId]) {
        return textInputs.value[choiceId]
      }

      return option?.text || ''
    })

    updateAnswer(selectedChoices.value, texts)
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
  <div class="multiple-choice-text-question">
    <div
      v-for="option in question.options"
      :key="option.id || 0"
      class="option-item"
      :class="{
        'with-text-input': option.allow_text,
        active: selectedChoices.includes(option.id!),
      }"
    >
      <Checkbox
        v-model="selectedChoices"
        :value="option.id"
        :inputId="`option-${option.id}`"
        :name="`question-${question.id}`"
      />
      <label :for="`option-${option.id}`">
        {{ option.text }}
      </label>
      <InputText
        v-if="option.allow_text && selectedChoices.includes(option.id!)"
        v-model="textInputs[option.id!]"
        type="text"
        :placeholder="'Additional text for ' + option.text"
        class="text-input"
      />
    </div>
  </div>
</template>
