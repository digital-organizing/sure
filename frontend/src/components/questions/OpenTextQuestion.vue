<script setup lang="ts">
import { ref, watch } from 'vue'
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
  remote?: ClientAnswerSchema | ConsultantAnswerSchema | null
  consultant?: boolean
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question, props.remote, props.consultant)
const textInput = ref<string>('')

// Load existing answer
if (answer.value.choices && answer.value.choices.length > 0) {
  textInput.value = answer.value.choices[0].text
}

// Update store when text changes
watch(textInput, (newText) => {
  updateAnswer(['1'], [newText])
})

function getAnswer() {
  return answer.value
}

defineExpose({
  getAnswer,
})
</script>

<template>
  <div class="open-text-question">
    <InputText v-model="textInput" type="text" :placeholder="question.question_text" />
  </div>
</template>
