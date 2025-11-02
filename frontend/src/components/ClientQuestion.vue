<script setup lang="ts">
import { defineProps, ref, computed } from 'vue'
import { type ClientAnswerSchema, type ClientQuestionSchema } from '@/client'
import { Form } from '@primevue/forms'
import SingleChoiceQuestion from './questions/SingleChoiceQuestion.vue'
import MultipleChoiceQuestion from './questions/MultipleChoiceQuestion.vue'
import OpenTextQuestion from './questions/OpenTextQuestion.vue'
import SingleChoiceTextQuestion from './questions/SingleChoiceTextQuestion.vue'
import MultipleChoiceTextQuestion from './questions/MultipleChoiceTextQuestion.vue'
import SingleChoiceDropdownQuestion from './questions/SingleChoiceDropdownQuestion.vue'

const props = defineProps<{
  question: ClientQuestionSchema
}>()

const questionComponentRef = ref<{ getAnswer: () => ClientAnswerSchema } | null>(null)

// Determine which component to use based on question format and options
const questionComponent = computed(() => {
  const format = props.question.format
  const hasDropdowns = props.question.options?.some(
    (option) => option.choices && option.choices.length > 0,
  )

  switch (format) {
    case 'single choice':
      return hasDropdowns ? SingleChoiceDropdownQuestion : SingleChoiceQuestion
    case 'multiple choice':
      return MultipleChoiceQuestion
    case 'single choice + open text field':
      return SingleChoiceTextQuestion
    case 'multiple choice + open text field':
      return MultipleChoiceTextQuestion
    case 'open text field':
      return OpenTextQuestion
    default:
      return SingleChoiceQuestion
  }
})

function getClientAnswer(): ClientAnswerSchema {
  if (questionComponentRef.value?.getAnswer) {
    return questionComponentRef.value.getAnswer()
  }

  // Fallback
  return {
    question: props.question.id!,
    choices: [],
    texts: [],
    created_at: new Date().toISOString(),
    user: null,
  }
}

defineExpose({
  getClientAnswer,
})
</script>

<template>
  <Form class="client-question">
    <p>{{ question.question_text }}</p>
    <component :is="questionComponent" ref="questionComponentRef" :question="question" />
  </Form>
</template>
