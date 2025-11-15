<script setup lang="ts">
import { useCase } from '@/composables/useCase'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTitle } from '@vueuse/core'
import PastVisitsComponent from '@/components/PastVisitsComponent.vue'
import HistoryComponent from '@/components/HistoryComponent.vue'
import { userAnswersStore } from '@/stores/answers'

const router = useRouter()

const props = defineProps<{
  caseId: string
}>()

useTitle(props.caseId + ' - Case View')

const { visit, setCaseId } = useCase()

const { clearAnswers } = userAnswersStore()

onMounted(() => {
  clearAnswers()
  setCaseId(props.caseId).then(() => {
    if (router.currentRoute.value.name !== 'consultant-case') {
      return
    }
    switch (visit.value!.status) {
      case 'consultant_submitted':
        router.replace({ name: 'consultant-tests', params: { caseId: props.caseId } })
        break
      case 'results_recorded':
      case 'communication':
        router.replace({ name: 'communication', params: { caseId: props.caseId } })
        break
      default:
        router.replace({ name: 'consultant-client-answers', params: { caseId: props.caseId } })
    }
  })
})
</script>

<template>
  <article>
    <aside>
      <section>
        General case information
        {{ visit }}
        <Button label="Refresh" @click="setCaseId(props.caseId)" />
      </section>
      <section>
        Past Visits
        <PastVisitsComponent />
      </section>
      <section>
        <HistoryComponent :caseId="props.caseId" />
      </section>
    </aside>
    <nav>
      Case navigation
      <RouterLink :to="{ name: 'consultant-client-answers', params: { caseId: props.caseId } }"
        >Client</RouterLink
      >
      <RouterLink :to="{ name: 'consultant-questionnaire', params: { caseId: props.caseId } }">
        Consultant</RouterLink
      >
      <RouterLink :to="{ name: 'consultant-tests', params: { caseId: props.caseId } }"
        >Tests</RouterLink
      >
    </nav>
    <section>
      <router-view />
    </section>
  </article>
</template>
