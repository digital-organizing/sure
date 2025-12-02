<script lang="ts" setup>
import { sureApiGetDocumentLink, type TestSchema } from '@/client'
import TestResultItem from './TestResultItem.vue'
import { useResults } from '@/composables/useResults'
import { computed } from 'vue'
import LocationComponent from './LocationComponent.vue'
import { useTexts } from '@/composables/useTexts'
import FreeFormResultItem from './FreeFormResultItem.vue'
import MarkdownIt from 'markdown-it'
import { formatDate } from '@vueuse/core'
import { saveAs } from 'file-saver'

const md = new MarkdownIt({
  linkify: true,
  html: true,
  breaks: true,
  typographer: true,
})

const props = defineProps<{
  caseId: string
  caseKey: string
}>()
const { tests, notes, documents, infos, caseStatus, location, freeFormTests } = useResults()

function downloadDocument(id: number) {
  sureApiGetDocumentLink({
    path: { doc_pk: id, pk: props.caseId },
    body: { key: props.caseKey },
  }).then((link) => {
    if (link.data) {
      saveAs(link.data.link, link.data.link.split('/').at(-1)?.split('?').at(0) || 'document')
    }
  })
}
function getResult(test: TestSchema, optionId: number) {
  return test.test_kind.result_options.find((option) => option.id == optionId)
}

function infoForOption(optionId: number) {
  return infos.value.find((info) => info.option === optionId)
}

const testsWithResults = computed(() => tests.value.filter((test) => test.results.length > 0))
const displayResults = computed(() => caseStatus.value && caseStatus.value.value != 'not_available')

const testCreationDate = computed(() => {
  const date = tests.value
    .map((test) => new Date(test.created_at))
    .sort((a, b) => new Date(a).getTime() - new Date(b).getTime())
    .at(0)

  if (!date) {
    return ''
  }
  return formatDate(date, 'DD.MM.YYYY')
})

const { getText: t, formatText: f } = useTexts()
</script>

<template>
  <section class="client-result">
    <h3>{{ t('your-results') }} ({{ props.caseId }})</h3>
    <!-- Display case results here -->
    <section v-if="!displayResults">
      {{ t('results-available-message') }}
      <LocationComponent :location="location" v-if="location" />
    </section>
    <section class="results" v-if="testsWithResults.length > 0 && displayResults">
      <div class="test-date">
        {{ f('tests-conducted-on', [{ key: 'date', value: testCreationDate }]) }}
      </div>
      <div v-for="test in testsWithResults" :key="test.id!" class="test-result">
        <TestResultItem
          :result="test.results[0]"
          :resultOption="getResult(test, test.results[0].result_option)!"
          :test="test"
          :infoText="infoForOption(test.results[0].result_option)?.information_text"
        />
      </div>
      <div v-for="test in freeFormTests" :key="test.id!" class="test-result">
        <FreeFormResultItem :result="test" />
      </div>
    </section>
    <Panel v-if="notes.length > 0 && displayResults" class="notes" :header="t('notes').value">
      <div v-for="note in notes" :key="note.id!" class="note">
        <p v-html="md.renderInline(note.note)"></p>
      </div>
    </Panel>
    <Panel
      class="documents"
      :header="t('documents').value"
      v-if="documents.length > 0 && displayResults"
      toggleable
    >
      <div v-for="document in documents" :key="document.id!" class="document">
        <p class="link" @click="downloadDocument(document.id!)">{{ document.name }}</p>
        <Button
          icon="pi pi-download"
          size="small"
          variant="outlined"
          @click="downloadDocument(document.id!)"
        />
      </div>
    </Panel>
  </section>
</template>

<style scoped>
.client-result {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  align-items: stretch;
}
h3 {
  text-align: center;
  display: inline;
  margin-bottom: 0;
}
.document {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.5rem;
}
.note {
  margin-bottom: 0.5rem;
}
.link {
  text-decoration: underline;
  font-weight: bold;
  color: var(--text-color);
  cursor: pointer;
}
.test-date {
  text-align: center;
}
</style>
