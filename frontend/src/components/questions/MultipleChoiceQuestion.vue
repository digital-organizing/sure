<script setup lang="ts">
import { ref, watch } from 'vue'
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
  remote?: ClientAnswerSchema | ConsultantAnswerSchema | null
  consultant?: boolean
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question, props.remote, props.consultant)
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

<style scoped>
.option-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.option-label {
  cursor: pointer;
}
</style>
