<script setup lang="ts">
import ClientQuestion from '@/components/ClientQuestion.vue'
import { useCase } from '@/composables/useCase'
import { onMounted } from 'vue'

const {
  onCaseId,
  loading,
  clientQuestionnaire,
  answerForClientQuestion,
  mapAnswersForClientQuestion,
  fetchClientSchema,
  fetchClientAnswers,
  clientAnswers,
} = useCase()

onMounted(() => {
  onCaseId(() => {
    console.log('Fetching client questionnaire for caseId')
    fetchClientAnswers()
    fetchClientSchema()
  })
})
</script>
<template>
  <section v-if="loading">Loading client questionnaire...</section>

  <section v-if="!loading && clientQuestionnaire && clientAnswers">
    <div v-for="section in clientQuestionnaire.sections" :key="section.id!">
      <h2>{{ section.title }}</h2>
      <div
        v-for="question in section.client_questions"
        :key="question.id!"
        style="margin-bottom: 20px"
      >
        <h3>{{ question.question_text }}</h3>
        <div v-for="answers in mapAnswersForClientQuestion(question.id!)" :key="answers.id">
          <p>
            <strong>Answer (code: {{ answers.code }}):</strong> {{ answers.text }}
          </p>
        </div>
        <ClientQuestion
          :question="question"
          :remote="answerForClientQuestion(question.id!)"
          ref="questionComponentRef"
        />
      </div>
    </div>
  </section>
</template>
