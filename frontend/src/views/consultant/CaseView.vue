<script setup lang="ts">
import { useCase } from '@/composables/useCase'
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { formatDate, useTitle } from '@vueuse/core'
import HistoryComponent from '@/components/HistoryComponent.vue'
import { userAnswersStore } from '@/stores/answers'
import { useStatus } from '@/composables/useStatus'

const router = useRouter()

const props = defineProps<{
  caseId: string
}>()

const navItems = [
  {
    label: 'Client',
    routeName: 'consultant-client-answers',
    status: 'client_submitted',
  },
  {
    label: 'Consultant',
    routeName: 'consultant-questionnaire',
    status: 'consultant_submitted',
  },
  {
    label: 'Tests',
    routeName: 'consultant-tests',
    status: 'tests_recorded',
  },
  {
    label: 'Summary',
    routeName: 'consultant-case-summary',
    status: 'summary',
  },
  {
    label: 'Results',
    routeName: 'consultant-results',
    status: 'results_recorded',
  },
  {
    label: 'Communication',
    routeName: 'consultant-communication',
    status: 'results_sent',
  },
]

useTitle(props.caseId + ' - Case View')

const { labelForStatus, indexForStatus } = useStatus()

function formatTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) {
    return 'N/A'
  }
  return formatDate(new Date(timestamp), 'DD.MM.YYYY HH:mm')
}

const { visit, setCaseId } = useCase()

const { clearAnswers } = userAnswersStore()

function isStatusDone(status: string): boolean {
  const caseStatusIndex = indexForStatus(visit.value?.status || '')
  const targetStatusIndex = indexForStatus(status)
  return caseStatusIndex >= targetStatusIndex
}

function isCurrentRoute(status: string): boolean {
  const route = router.currentRoute.value
  const item = navItems.find((item) => item.status === status)
  if (!item) {
    return false
  }
  return route.name === item.routeName
}

const inHistoryView = computed(() => {
  return router.currentRoute.value.name === 'consultant-case-history'
})

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
    <h1>Case-ID {{ props.caseId }}</h1>

    <div class="refresh">
      <Button icon="pi pi-refresh" @click="setCaseId(props.caseId)" severity="secondary" />
    </div>
    <aside>
      <Panel header="Case Details">
        <div class="case-field">
          <span class="label">Client ID</span>
          <span>{{ visit?.client || '-' }}</span>
        </div>
        <div class="case-field">
          <span class="label">Case ID</span>
          <span>{{ visit?.case }}</span>
        </div>
        <div class="case-field">
          <span class="label">Location</span>
          <span>{{ visit?.location }}</span>
        </div>
        <div class="case-field">
          <span class="label">Last Modification</span>
          <span>{{ formatTimestamp(visit?.last_modified_at) }}</span>
        </div>
        <div class="case-field">
          <span class="label">Created At</span>
          <span>{{ formatTimestamp(visit?.created_at) }}</span>
        </div>
        <div class="case-field status">
          <span class="label"> Status </span>
          <Tag :value="labelForStatus(visit?.status!)" :class="visit?.status" rounded />
        </div>
        <div class="case-field">
          <span class="label">Tags</span>
          <div class="tags">
            <Tag v-for="tag in visit?.tags" :key="tag" :value="tag" rounded severity="secondary" />
          </div>
        </div>
      </Panel>
      <Panel header="History" v-if="!inHistoryView">
        <HistoryComponent :caseId="props.caseId" />
      </Panel>
    </aside>
    <section class="case-main">
      <nav v-if="!inHistoryView">
        <RouterLink
          v-for="item in navItems"
          :to="{ name: item.routeName, params: { caseId: props.caseId } }"
          :key="item.status"
          :class="[
            'nav-pill',
            item.status,
            isStatusDone(item.status) ? 'done' : 'open',
            isCurrentRoute(item.status) ? 'current' : '',
          ]"
          >{{ item.label }}</RouterLink
        >
      </nav>
      <nav v-else>
        <Button
          icon="pi pi-arrow-left"
          severity="secondary"
          class="nav-pill done"
          @click="router.back()"
          label="Back"
        />
      </nav>
      <router-view />
    </section>
  </article>
</template>

<style scoped>
article {
  display: grid;
  grid-template-areas: 'title title refresh' 'side main main';
  grid-template-columns: auto 1fr;
  padding-left: 1rem;
  padding-right: 1rem;
}

.nav-pill {
  transition: all 0.3s ease;
}

h1 {
  grid-area: title;
  margin-bottom: 1rem;
}

aside {
  grid-area: side;
  border-right: 1px solid var(--border-color);
  padding-right: 1rem;
  margin-right: 1rem;
  display: flex;
  flex-direction: column;
  width: 250px;
  gap: 1rem;
}

.case-main {
  grid-area: main;
}

nav {
  display: flex;
  gap: 3px;
  margin-bottom: 1rem;
}

.done {
  align-self: flex-start;
}

.current {
  margin-right: auto;
}

.open:first {
  align-self: flex-end;
  margin-left: auto;
}

nav a {
  text-decoration: none;
  background-color: var(--status-color);
  color: white;
  padding: 5px 20px;
  border-radius: 40px;
}

.tags {
  margin-top: 3px;
  display: flex;
  gap: 3px;
  flex-wrap: wrap;
}

.case-field {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.case-field .label {
  font-weight: bold;
}
</style>
