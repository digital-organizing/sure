<script setup lang="ts">
import { ref, computed } from 'vue'
import { type ConsultantAnswerSchema, type ConsultantQuestionSchema } from '@/client'
import SingleChoiceQuestion from './questions/SingleChoiceQuestion.vue'
import MultipleChoiceQuestion from './questions/MultipleChoiceQuestion.vue'
import OpenTextQuestion from './questions/OpenTextQuestion.vue'
import SingleChoiceTextQuestion from './questions/SingleChoiceTextQuestion.vue'
import MultipleChoiceTextQuestion from './questions/MultipleChoiceTextQuestion.vue'
import SingleChoiceDropdownQuestion from './questions/SingleChoiceDropdownQuestion.vue'
import MultiChoiceMultiTextQuestion from './questions/MultiChoiceMultiTextQuestion.vue'
import { useCase } from '@/composables/useCase'

const props = defineProps<{
  question: ConsultantQuestionSchema
}>()

const questionComponentRef = ref<{ getAnswer: () => ConsultantAnswerSchema } | null>(null)

const { answerForConsultantQuestion } = useCase()

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
    case 'long text field':
      return OpenTextQuestion
    case 'multiple choice + multiple open text field':
      return MultiChoiceMultiTextQuestion
    default:
      return SingleChoiceQuestion
  }
})

function getConsultantAnswer(): ConsultantAnswerSchema {
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

const remote = computed(() => {
  return computed(() => answerForConsultantQuestion(props.question.id!) || null)
})

defineExpose({
  getConsultantAnswer,
})
</script>

<template>
  <component
    :is="questionComponent"
    ref="questionComponentRef"
    :question="question"
    :remote="remote"
    :consultant="true"
  />
</template>
