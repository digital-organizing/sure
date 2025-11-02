<script setup lang="ts">
import { ref, watch } from 'vue'
import { InputText } from 'primevue'
import { type ClientQuestionSchema } from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'

const props = defineProps<{
  question: ClientQuestionSchema
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question)
const textInput = ref<string>('')

// Load existing answer
if (answer.value.texts && answer.value.texts.length > 0) {
  textInput.value = answer.value.texts[0] as string
}

// Update store when text changes
watch(textInput, (newText) => {
  updateAnswer([], [newText])
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
