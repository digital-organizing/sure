<script setup lang="ts">
import { ref, watch } from 'vue'
import { Checkbox } from 'primevue'
import { type ClientQuestionSchema } from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'

const props = defineProps<{
  question: ClientQuestionSchema
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question)
const selectedChoices = ref<string[]>([])

// Load existing answer
if (answer.value.choices && answer.value.choices.length > 0) {
  selectedChoices.value = [...answer.value.choices.map((choice) => choice.code)]
}

// Update store when selection changes
watch(
  selectedChoices,
  (newChoices) => {
    const texts = newChoices.map((choiceId) => {
      const option = props.question.options?.find((opt) => opt.code === choiceId)
      return option?.text || ''
    })
    updateAnswer(newChoices, texts)
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
  <div class="multiple-choice-question">
    <div v-for="option in question.options" :key="option.id || 0" class="client-option-item">
      <Checkbox
        v-model="selectedChoices"
        :value="option.code"
        :inputId="`option-${option.id}`"
        :name="`question-${question.id}`"
      />
      <label :for="`option-${option.id}`" class="client-option-label">
        {{ option.text }}
      </label>
    </div>
  </div>
</template>
