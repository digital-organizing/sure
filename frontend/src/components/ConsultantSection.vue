<script setup lang="ts">
import type { ClientQuestionSchema, SectionSchema } from '@/client'
import { userAnswersStore } from '@/stores/answers'
import { computed, ref } from 'vue'
import ClientQuestionConsultant from './ClientQuestionConsultant.vue'

const props = defineProps<{
  section: SectionSchema
}>()

const show = ref(false)

const answerStore = userAnswersStore()

function showQuestion(q: ClientQuestionSchema) {
  if (!q.show_for_options || q.show_for_options.length === 0) {
    return true
  }

  return q.show_for_options.some((option) => answerStore.isOptionSelected(option))
}

const questions = computed(() => {
  return props.section?.client_questions.filter((question) => showQuestion(question)) || []
})
</script>

<template>
  <header v-if="section.client_questions.length > 0">
    <h2>{{ section.title }}</h2>
    <Button icon="pi pi-eye" size="small" severity="secondary" @click="show = !show" />
  </header>
  <section v-if="show" class="section">
    <div v-for="question in questions" :key="question.id!">
      <ClientQuestionConsultant :question="question" />
    </div>
  </section>
</template>

<style scoped>
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}
</style>
