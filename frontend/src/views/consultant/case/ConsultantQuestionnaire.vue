<script lang="ts" setup>
import ConsultantQuestion from '@/components/ConsultantQuestion.vue'
import { useCase } from '@/composables/useCase'
import { onMounted } from 'vue'

const {
  onCaseId,
  loading,
  fetchConsultantAnswers,
  fetchConsultantSchema,
  consultantQuestionnaire,
  answerForConsultantQuestion,
  mapAnswersForConsultantQuestion,
} = useCase()

onMounted(() => {
  onCaseId(() => {
    fetchConsultantSchema()
    fetchConsultantAnswers()
  })
})
</script>

<template>
  <div v-if="loading">Loading consultant questionnaire...</div>
  <div v-else>
    Consultant Questionnaire Content
    <div v-for="question in consultantQuestionnaire?.consultant_questions" :key="question.id!">
      <h3>{{ question.question_text }}</h3>
      <div v-for="answers in mapAnswersForConsultantQuestion(question.id!)" :key="answers.id">
        <p>
          <strong>Answer (code: {{ answers.code }}):</strong> {{ answers.text }}
        </p>
      </div>

      <ConsultantQuestion
        :question="question"
        :remote="answerForConsultantQuestion(question.id!)"
      />
    </div>
  </div>
</template>
