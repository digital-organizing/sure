<script setup lang="ts">
import { defineProps, ref, computed, type ComputedRef } from 'vue'
import { type AnswerSchema, type ClientAnswerSchema, type ClientQuestionSchema } from '@/client'
import { Form } from '@primevue/forms'
import SingleChoiceQuestion from './questions/SingleChoiceQuestion.vue'
import MultipleChoiceQuestion from './questions/MultipleChoiceQuestion.vue'
import OpenTextQuestion from './questions/OpenTextQuestion.vue'
import SingleChoiceTextQuestion from './questions/SingleChoiceTextQuestion.vue'
import MultipleChoiceTextQuestion from './questions/MultipleChoiceTextQuestion.vue'
import SingleChoiceDropdownQuestion from './questions/SingleChoiceDropdownQuestion.vue'
import MultiChoiceMultiTextQuestion from './questions/MultiChoiceMultiTextQuestion.vue'

const props = defineProps<{
  question: ClientQuestionSchema
  index?: number
  remote?: ComputedRef<ClientAnswerSchema | null>
  hideTitle: boolean
}>()

const questionComponentRef = ref<{ getAnswer: () => AnswerSchema } | null>(null)

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
      console.warn(`Unknown question format: ${format}, defaulting to SingleChoiceQuestion.`)
      return SingleChoiceQuestion
  }
})

const showQuestionNumber = computed(() => props.question.code !== 'CONSULT-WISH')
function getClientAnswer(): AnswerSchema {
  if (questionComponentRef.value?.getAnswer) {
    return questionComponentRef.value.getAnswer()
  }

  // Fallback
  return {
    choices: [],
    questionId: props.question.id!,
  }
}

defineExpose({
  getClientAnswer,
})
</script>

<template>
  <Form class="client-question">
    <div class="question-title">
      <div v-if="showQuestionNumber && index !== undefined" class="question-number">
        {{ index + 1 }}
      </div>
      <div class="question-content">
        <p class="question-text" v-if="!hideTitle">{{ question.question_text }}</p>
        <component :is="questionComponent" ref="questionComponentRef" :question="question" />
      </div>
    </div>
  </Form>
</template>

<style scoped>
.question-title {
  display: flex;
  flex-direction: row;
  align-items: top;
  gap: 16px;
  margin-bottom: 1rem;
  margin-top: 0.5rem;
}

.question-text {
  color: var(--color-ahs-black);
  font-family: 'Circular Std';
  font-size: 18px;
  font-style: normal;
  font-weight: 700;
  line-height: 20px; /* 111.111% */
  margin-bottom: 10px;
  margin-top: 12.5px;
}

.question-content {
  flex: 1;
  width: calc(100% - 40px);
}

.question-number {
  color: var(--color-ahs-white);
  text-align: center;
  font-family: 'Circular Std';
  font-size: 24px;
  font-style: normal;
  font-weight: 700;
  line-height: 40px;
  border-radius: 10rem;
  background-color: #000;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
}
</style>
