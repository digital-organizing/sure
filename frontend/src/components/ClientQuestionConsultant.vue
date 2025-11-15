<script lang="ts" setup>
import type { AnswerSchema, ClientQuestionSchema } from '@/client'
import { useCase } from '@/composables/useCase'
import ClientQuestion from './ClientQuestion.vue'
import { computed, ref } from 'vue'

const props = defineProps<{
  question: ClientQuestionSchema
}>()

const questionComponentRef = ref<{ getClientAnswer: () => AnswerSchema } | null>(null)

const {
  answerForClientQuestion,
  mapAnswersForClientQuestion,
  submitClientAnswer,
  fetchVisitDetails,
} = useCase()

function onSubmit() {
  if (questionComponentRef.value) {
    const answer = questionComponentRef.value.getClientAnswer()
    submitClientAnswer(answer).then(() => {
      fetchVisitDetails()
    })
  }
}

const remote = computed(() => {
  return answerForClientQuestion(props.question.id!)
})
</script>

<template>
  <h3>{{ props.question.question_text }}</h3>
  <div v-for="answers in mapAnswersForClientQuestion(question.id!)" :key="answers.id">
    <p>
      <strong>Answer (code: {{ answers.code }}):</strong> {{ answers.text }}
    </p>
  </div>
  <ClientQuestion :question="question" :remote="remote" ref="questionComponentRef" />
  <Button label="Submit Answer" @click.prevent="onSubmit()" />
</template>
