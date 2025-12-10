<script lang="ts" setup>
import { sureApiGetNonSmsResults, sureApiGetPhoneNumber, type TestSchema } from '@/client'
import CaseNoteComponent from '@/components/CaseNoteComponent.vue'
import ClientResult from '@/components/ClientResult.vue'
import DocumentUploadComponent from '@/components/DocumentUploadComponent.vue'
import { useCase } from '@/composables/useCase'
import { useResults } from '@/composables/useResults'
import { useTexts } from '@/composables/useTexts'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{ caseId: string }>()
const { getText: t } = useTexts()

const { publishResults, setCaseStatus, onCaseRefresh, visit } = useCase()
const phoneNumber = ref<string>('')
const hasPhoneNumber = ref(false)
const nonSmsResults = ref<TestSchema[]>([])

function getPhoneNumber() {
  sureApiGetPhoneNumber({ path: { pk: props.caseId } }).then((response) => {
    if (response.data && response.data.success) {
      phoneNumber.value = '' + response.data.message
      hasPhoneNumber.value = true
    } else if (response.data && !response.data.success) {
      phoneNumber.value = '' + response.data.message
      hasPhoneNumber.value = false
    }
  })
}

const router = useRouter()
const { fetchCase, caseStatus } = useResults()

onMounted(async () => {
  fetchCase(props.caseId, '', false)
  sureApiGetNonSmsResults({ path: { pk: props.caseId } }).then((response) => {
    if (Array.isArray(response.data)) {
      nonSmsResults.value = response.data.filter((test) => test.results.length > 0)
    }
  })
  onCaseRefresh(async () => {
    await fetchCase(props.caseId, '', false)
  })
})

function onBack() {
  router.push({ name: 'consultant-results', params: { caseId: props.caseId } })
}

function onPublishResults() {
  publishResults()
}

function makeCall(number: string) {
  window.open(`tel:${number}`, '_self')
}
</script>

<template>
  <header class="case">
    <h2>Communication</h2>
  </header>
  <div class="case-row">
    <section class="client-preview">
      <section class="notes">
        <Message severity="info">
          {{ t('client-preview-info') }}
        </Message>
        <Message severity="warn" v-if="caseStatus?.value == 'not_available'">
          {{ t('non-sms-results-warning') }}
        </Message>
      </section>
      <Panel class="preview-panel">
        <ClientResult :caseId="props.caseId" :caseKey="''" class="preview" />
      </Panel>
    </section>

    <section class="results" v-if="caseStatus?.value == 'not_available'">
      <h4>{{ t('non-sms-results-title') }}</h4>
      <div
        v-for="test in nonSmsResults"
        :key="test.id!"
        :style="{
          '--result-color': test.results[0]
            ? test.test_kind.result_options.find(
                (option) => option.id === test.results[0].result_option,
              )?.color || '#000'
            : '#000',
        }"
        class="non-sms-result"
      >
        <span class="test-name">
          {{ test.test_kind.name }}
        </span>

        <span class="result">
          {{
            test.test_kind.result_options.find(
              (option) => option.id === test.results[0].result_option,
            )?.label
          }}
        </span>
      </div>
    </section>

    <section class="row">
      <CaseNoteComponent class="row" />
    </section>

    <section class="row">
      <DocumentUploadComponent :caseId="props.caseId" />
    </section>
  </div>

  <section class="case-footer">
    <Button :label="t('back').value" severity="secondary" @click="onBack()" />

    <div class="actions">
      <Button
        :label="t('show-phone-number').value"
        severity="secondary"
        @click="getPhoneNumber()"
        v-if="phoneNumber === ''"
      />
      <Button
        icon="pi pi-phone"
        v-if="phoneNumber !== ''"
        class="phonenumber"
        :label="phoneNumber"
        severity="secondary"
        :disabled="!hasPhoneNumber"
        @click="makeCall(phoneNumber)"
      />
      <Button
        :label="t('reset-case-to-recorded').value"
        v-if="
          visit?.status === 'results_missed' ||
          visit?.status === 'closed' ||
          visit?.status === 'results_seen'
        "
        @click="
          setCaseStatus('results_recorded').then(() => {
            fetchCase(props.caseId, '', false)
          })
        "
      ></Button>
      <Button
        :label="t('client-accessed-results').value"
        v-if="visit?.status != 'results_seen'"
        @click="
          setCaseStatus('results_seen').then(() => {
            fetchCase(props.caseId, '', false)
          })
        "
        severity="secondary"
      ></Button>
      <Button
        :label="t('publish-results').value"
        v-if="caseStatus?.value == 'results_recorded'"
        severity="primary"
        @click="onPublishResults"
      ></Button>
    </div>
  </section>
</template>

<style scoped>
.client-preview {
  max-width: 500px;
}
.preview-panel {
  max-height: 520px;
  overflow-y: auto;
  margin-top: 1rem;
  margin-bottom: 1rem;
}
.non-sms-result {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.3rem;
}
.result {
  background-color: var(--result-color);
  color: white;
  padding: 0.2rem 0.5rem;
  border-radius: 5px;
  font-weight: bold;
}

section.results {
  margin-top: 1rem;
  margin-bottom: 1rem;
}

.notes {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.actions {
  display: flex;
  gap: 0.5rem;
}
.row {
  margin-top: 1rem;
}
</style>
