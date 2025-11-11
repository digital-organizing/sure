<script setup lang="ts">
import type { ClientQuestionSchema } from '@/client'
import ClientQuestionConsultant from '@/components/ClientQuestionConsultant.vue'
import { useCase } from '@/composables/useCase'
import { userAnswersStore } from '@/stores/answers'
import { onMounted } from 'vue'

const { onCaseId, loading, fetchClientSchema, fetchClientAnswers, clientAnswers } = useCase()

const answerStore = userAnswersStore()

onMounted(() => {
  onCaseId(() => {
    fetchClientAnswers()
    fetchClientSchema()
  })
})

function showQuestion(q: ClientQuestionSchema) {
  if (!q.show_for_options || q.show_for_options.length === 0) {
    return true
  }

  return q.show_for_options.some((option) => answerStore.isOptionSelected(option))
}
</script>
<template>
  <section v-if="loading">Loading client questionnaire...</section>

  <section v-if="answerStore.schema && clientAnswers">
    <div v-for="section in answerStore.schema.sections" :key="section.id!">
      <h2>{{ section.title }}</h2>
      <div
        v-for="question in section.client_questions"
        :key="question.id!"
        style="margin-bottom: 20px"
      >
        <ClientQuestionConsultant v-if="showQuestion(question)" :question="question" />
      </div>
    </div>
  </section>
</template>
