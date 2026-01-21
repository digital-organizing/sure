<script setup lang="ts">
import { useCase } from '@/composables/useCase'
import { computed, onActivated, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { formatDate, useClipboard, useTitle } from '@vueuse/core'
import HistoryComponent from '@/components/HistoryComponent.vue'
import { useStatus } from '@/composables/useStatus'
import { useTexts } from '@/composables/useTexts'
import { useToast } from 'primevue/usetoast'

import { useConfirm } from 'primevue/useconfirm'

const router = useRouter()
const { getText: t } = useTexts()

const props = defineProps<{
  caseId: string
}>()

const navItems = computed(() => [
  {
    label: t('nav-client').value,
    routeName: 'consultant-client-answers',
    status: 'client_submitted',
  },
  {
    label: t('nav-consultant').value,
    routeName: 'consultant-questionnaire',
    status: 'consultant_submitted',
  },
  {
    label: t('nav-tests').value,
    routeName: 'consultant-tests',
    status: 'tests_recorded',
  },
  {
    label: t('nav-summary').value,
    routeName: 'consultant-case-summary',
    status: 'summary',
  },
  {
    label: t('nav-results').value,
    routeName: 'consultant-results',
    status: 'results_recorded',
  },
  {
    label: t('nav-communication').value,
    routeName: 'consultant-communication',
    status: 'results_sent',
  },
])

const title = computed(() => 'Case ' + props.caseId + ' - Case View')

const editExternalId = ref(false)
const newExternalId = ref('')

useTitle(title)

const toast = useToast()

const { labelForStatus, indexForStatus } = useStatus()

function formatTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) {
    return 'N/A'
  }
  return formatDate(new Date(timestamp), 'DD.MM.YYYY HH:mm')
}

const { visit, setCaseId, relatedCases, loading, setCaseStatus, updateInternalId } = useCase()

function isStatusDone(status: string): boolean {
  const caseStatusIndex = indexForStatus(visit.value?.status || '')
  const targetStatusIndex = indexForStatus(status)
  return caseStatusIndex >= targetStatusIndex
}

function isCurrentRoute(status: string): boolean {
  const route = router.currentRoute.value
  const item = navItems.value.find((item) => item.status === status)
  if (!item) {
    return false
  }
  return route.name === item.routeName
}

const inHistoryView = computed(() => {
  return router.currentRoute.value.name === 'consultant-case-history'
})

function copyClientLink() {
  const { copy } = useClipboard()
  const clientLink = `${window.location.origin}/client/${props.caseId}`
  copy(clientLink)

  toast.add({
    severity: 'success',
    summary: t('client-link-copied').value,
    detail: t('client-link-copied-detail').value,
    life: 3000,
  })
}

const confirm = useConfirm()

const confirmCancel = () => {
  confirm.require({
    message: t('confirm-cancel-case-message').value,
    header: t('confirm-cancel-case-header').value,
    icon: 'pi pi-exclamation-triangle',
    accept: () => {
      setCaseStatus('canceled')
    },
    reject: () => {
      /* no action */
    },
  })
}

const confirmClose = () => {
  confirm.require({
    message: t('confirm-close-case-message').value,
    header: t('confirm-close-case-header').value,
    icon: 'pi pi-exclamation-triangle',
    accept: () => {
      setCaseStatus('closed')
    },
    reject: () => {
      /* no action */
    },
  })
}

function cleanId(id: string): string {
  if (id.startsWith('EXT-')) {
    return id.slice(4)
  }
  return id
}

onMounted(async () => {
  // If scrolled down, scroll to top when changing case
  if (window.scrollY > 200) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  if (props.caseId !== visit.value?.case) {
    await setCaseId(props.caseId)
  }
  if (router.currentRoute.value.name !== 'consultant-case') {
    return
  }
  newExternalId.value = cleanId(visit.value?.external_id || '')
  console.log(visit.value?.external_id)
  switch (visit.value!.status) {
    case 'client_submitted':
      router.replace({ name: 'consultant-client-answers', params: { caseId: props.caseId } })
      break
    case 'consultant_submitted':
      router.replace({ name: 'consultant-tests', params: { caseId: props.caseId } })
      break
    case 'tests_recorded':
      router.replace({ name: 'consultant-results', params: { caseId: props.caseId } })
      break
    case 'results_seen':
    case 'closed':
      router.replace({ name: 'consultant-case-summary', params: { caseId: props.caseId } })
      break
    case 'results_recorded':
    case 'results_sent':
    case 'results_missed':
    case 'communication':
      router.replace({ name: 'consultant-communication', params: { caseId: props.caseId } })
      break
    default:
      router.replace({ name: 'consultant-client-answers', params: { caseId: props.caseId } })
  }
})

watch(
  () => props.caseId,
  (newCaseId) => {
    setCaseId(newCaseId)
  },
)
</script>

<template>
  <article :class="loading ? 'loading' : ''">
    <h1>{{ t('case-id-title') }} {{ props.caseId }}</h1>

    <div class="refresh">
      <Button icon="pi pi-refresh" @click="setCaseId(props.caseId)" severity="secondary" />
    </div>
    <aside>
      <Panel :header="t('case-details').value">
        <div class="case-field">
          <span class="label">{{ t('client-id') }}</span>
          <span class="value">{{ visit?.client || '-' }}</span>
        </div>
        <div class="case-field">
          <span class="label">{{ t('phone') }}</span>
          <span class="value">{{ visit?.client ? t('yes') : t('no') }}</span>
        </div>
        <div class="case-field">
          <span class="label">{{ t('case-id') }}</span>
          <span class="value">{{ visit?.case }}</span>
        </div>
        <div></div>
        <div class="case-field">
          <span class="label">{{ t('location') }}</span>
          <span class="value">{{ visit?.location }}</span>
        </div>
        <div class="case-field">
          <span class="label">{{ t('last-modification') }}</span>
          <span class="value">{{ formatTimestamp(visit?.last_modified_at) }}</span>
        </div>
        <div class="case-field">
          <span class="label">{{ t('created-at') }}</span>
          <span class="value">{{ formatTimestamp(visit?.created_at) }}</span>
        </div>
        <div class="case-field status">
          <span class="label"> {{ t('status') }} </span>
          <Tag :value="labelForStatus(visit?.status!)" :class="visit?.status" rounded />
        </div>
        <div class="case-field">
          <span class="label">{{ t('external-id') }}</span>
          <div class="external-edit">
            <span class="value" v-if="!editExternalId">{{ visit?.external_id }}</span>
            <Button
              v-if="!editExternalId"
              icon="pi pi-pencil"
              severity="secondary"
              size="small"
              @click="
                ((editExternalId = true),
                (newExternalId = visit?.external_id ? cleanId(visit.external_id) : ''))
              "
            />
            <InputText
              v-if="editExternalId"
              v-model="newExternalId"
              type="text"
              class="text-input"
            />
            <Button
              v-if="editExternalId"
              icon="pi pi-check"
              severity="success"
              size="small"
              @click="updateInternalId(newExternalId).then(() => (editExternalId = false))"
            />
          </div>
        </div>
        <div class="case-field">
          <span class="label">{{ t('preferred-language') }}</span>
          <span class="value">{{ visit?.language || '-' }}</span>
        </div>

        <div class="case-field">
          <span class="label">{{ t('tags') }}</span>
          <div class="tags">
            <Tag v-for="tag in visit?.tags" :key="tag" :value="tag" rounded severity="secondary" />
          </div>
        </div>
        <div class="history case-field" v-if="relatedCases && relatedCases.length > 0">
          <span class="label">{{ t('past-visits') }}</span>
          <div class="visits">
            <RouterLink
              v-for="relatedCase in relatedCases"
              :key="relatedCase.case_id!"
              :to="{ name: 'consultant-case-summary', params: { caseId: relatedCase.case_id } }"
              >{{ formatDate(new Date(relatedCase.created_at), 'DD.MM.YYYY') }}</RouterLink
            >
          </div>
        </div>

        <template #footer>
          <Button
            :label="t('copy-client-link').value"
            size="small"
            variant="outlined"
            severity="secondary"
            v-if="visit?.status == 'created'"
            @click="copyClientLink()"
          ></Button>
        </template>
      </Panel>
      <Panel :header="t('history').value" v-if="!inHistoryView">
        <HistoryComponent :caseId="props.caseId" />
      </Panel>
      <Panel :header="t('actions').value">
        <div class="actions">
          <Button
            :label="t('cancel-case').value"
            severity="secondary"
            @click="confirmCancel()"
            v-if="visit?.status != 'canceled' && visit?.status != 'closed'"
          ></Button>
          <Button
            :label="t('close-case').value"
            severity="secondary"
            @click="confirmClose()"
            v-if="visit?.status != 'closed' && visit?.status != 'canceled'"
          ></Button>
          <Button
            :label="t('back').value"
            severity="secondary"
            @click="router.push({ name: 'consultant-dashboard' })"
          />
        </div>
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
          :label="t('back').value"
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
  gap: 1rem;
}

.external-edit {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.external-edit .p-inputtext {
  flex: 1 1 auto;
  width: 0;
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
  display: flex;
  flex-direction: column;
  width: 250px;
  gap: 1rem;
}

.case-main {
  grid-area: main;
  display: flex;
  flex-direction: column;
}

nav {
  display: flex;
  gap: 3px;
  margin-bottom: 1rem;

  overflow-x: auto;
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
  font-weight: normal;
}

.case-field .value {
  font-weight: bold;
  margin-top: 0.2rem;
}

@media screen and (max-width: 600px) {
  article {
    grid-template-areas:
      'title title refresh'
      'main main main'
      'side side side';
    grid-template-columns: 1fr;
  }

  aside {
    border-right: none;
    border-top: 1px solid var(--border-color);
    padding-right: 0;
    margin-right: 0;
    width: 100%;
    display: flex;
    flex-direction: row;
    gap: 1rem;
    flex-wrap: wrap;
  }

  aside .p-panel {
    flex: 1;
  }
}

.visits {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex-wrap: wrap;
}

.visits a {
  text-decoration: underline;
  font-weight: bold;
  color: var(--text-color);
}

.actions {
  display: flex;
  gap: 0.5rem;
  flex-direction: column;
}
</style>
