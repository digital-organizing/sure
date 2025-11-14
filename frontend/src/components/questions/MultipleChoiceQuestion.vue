<script setup lang="ts">
import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
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
  remote?: ComputedRef<ClientAnswerSchema | ConsultantAnswerSchema | null>,
  consultant?: boolean
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question, props.remote, props.consultant)
const selectedChoices = computed<string[]>({
  get() {
    console.log(props.question.id, 'Getting selected choices from answer:', answer.value)
    return [...answer.value.choices.map((choice) => choice.code)]
  },
  set(newChoices: string[]) {
    console.log(props.question.id, 'Setting selected choices to:', newChoices)
    const texts = newChoices.map((choiceId) => {
      const option = props.question.options?.find((opt) => opt.code === choiceId)
      return option?.text || ''
    })
    updateAnswer(newChoices, texts)
  },
    
})

// Load existing answer
// if (answer.value.choices && answer.value.choices.length > 0) {
//   selectedChoices.value = [...answer.value.choices.map((choice) => choice.code)]
// }


// Update store when selection changes
// watch(
//   selectedChoices,
//   (newChoices) => {
//     const texts = newChoices.map((choiceId) => {
//       const option = props.question.options?.find((opt) => opt.code === choiceId)
//       return option?.text || ''
//     })
//     updateAnswer(newChoices, texts)
//   },
//   { deep: true },
// )

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
