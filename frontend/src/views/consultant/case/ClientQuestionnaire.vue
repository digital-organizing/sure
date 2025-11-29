<script setup lang="ts">
import ConsultantSection from '@/components/ConsultantSection.vue'
import { useCase } from '@/composables/useCase'
import { userAnswersStore } from '@/stores/answers'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'


const router = useRouter()
const { onCaseId, loading, fetchClientSchema, fetchClientAnswers, clientAnswers, visit } = useCase()

const answerStore = userAnswersStore()

onMounted(() => {
  onCaseId(() => {
    fetchClientAnswers()
    fetchClientSchema()
  })
})

function onBack() {
  router.push({ name: 'consultant-dashboard' })
}

function onNext() {
  router.push({ name: 'consultant-questionnaire', params: { caseId: visit.value?.case } })
}
</script>
<template>
  <section v-if="loading">Loading client questionnaire...</section>

  <section v-if="answerStore.schema && clientAnswers !== null">
    <header class="case">
      <h2>Client Questionnaire</h2>
    </header>
    <div v-for="section in answerStore.schema.sections" :key="section.id!" class="section">
      <ConsultantSection :section="section" />
    </div>
  </section>
  <footer class="case-footer">
    <Button label="Back" severity="secondary" @click="onBack()" />
    <Button label="Next" severity="primary" @click="onNext()" />
  </footer>
</template>

<style scoped>
.section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 0.5rem;
}
</style>
