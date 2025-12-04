<script setup lang="ts">
import type { ClientQuestionSchema, SectionSchema } from '@/client'
import { userAnswersStore } from '@/stores/answers'
import { computed, ref } from 'vue'
import ClientQuestionConsultant from './ClientQuestionConsultant.vue'

const props = defineProps<{
  section: SectionSchema
  disableEdit?: boolean
}>()

const show = ref(true)
const showAll = ref(false)

const answerStore = userAnswersStore()

function showQuestion(q: ClientQuestionSchema) {
  if (!q.show_for_options || q.show_for_options.length === 0) {
    return true
  }

  return q.show_for_options.some((option) => answerStore.isOptionSelected(option))
}

const hasHiddenQuestions = computed(() => {
  return props.section.client_questions.some(
    (question) => question.do_not_show_directly && showQuestion(question),
  )
})

const questions = computed(() => {
  return (
    props.section?.client_questions.filter(
      (question) => showQuestion(question) && (showAll.value || !question.do_not_show_directly),
    ) || []
  )
})
</script>

<template>
  <header v-if="section.client_questions.length > 0">
    <h3>{{ section.label || section.title }}</h3>
    <div class="buttons">
      <Button
        :icon="showAll ? 'pi pi-search-minus' : 'pi pi-search-plus'"
        size="small"
        severity="secondary"
        v-if="hasHiddenQuestions && show"
        @click="showAll = !showAll"
        title="Show hidden questions"
      />
      <Button
        :icon="show ? 'pi pi-eye-slash' : 'pi pi-eye'"
        size="small"
        severity="secondary"
        @click="show = !show"
        title="Expand section"
      />
    </div>
  </header>
  <section v-if="show" class="section">
    <div v-for="question in questions" :key="question.id!">
      <ClientQuestionConsultant :question="question" :disable-edit="props.disableEdit" />
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
  margin-bottom: 1rem;
}
h3 {
  margin: 0;
}
.buttons {
  display: flex;
  gap: 0.5rem;
}
</style>
