<script setup lang="ts">
import { computed, type ComputedRef } from 'vue'
import { InputText } from 'primevue'
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
const textInput = computed<string>({
  get() {
    return answer.value.choices[0]?.text || ''
  },
  set(newText: string) {
    updateAnswer(['1'], [newText])
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
  <div>
    <InputText
      v-model="textInput"
      type="text"
      :placeholder="question.question_text"
      class="text-input"
      v-if="question.format == 'open text field'"
    />
    <Textarea
      v-model="textInput"
      :placeholder="question.question_text"
      auto-resize
      :rows="5"
      class="text-input"
      v-if="question.format == 'long text field'"
    />
  </div>
</template>

<style lang="css" scoped>
.text-input {
  margin-bottom: 0.5rem;
}
textarea.text-input {
  width: 100%;
}
div {
  align-self: stretch;
  display: flex;
  flex-direction: column;
}
</style>
