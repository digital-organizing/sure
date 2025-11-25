<script setup lang="ts">
import { type ClientQuestionSchema, type ConsultantQuestionSchema } from '@/client'
import ConsultantSection from '@/components/ConsultantSection.vue'
import { useCase } from '@/composables/useCase'
import { useTests } from '@/composables/useTests'
import { userAnswersStore } from '@/stores/answers'
import { useClipboard } from '@vueuse/core'
import { useToast } from 'primevue'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

defineProps<{
  caseId: string
}>()

const router = useRouter()
const {
  mapAnswersForClientQuestion,
  mapAnswersForConsultantQuestion,
  selectedTests,
  freeFormTests,
  clientAnswers,
  visit,
  consultantQuestionnaire,
} = useCase()
const { testKinds } = useTests()

const showClient = ref(false)
const showConsultant = ref(true)

const { copy } = useClipboard()
const toast = useToast()

const answerStore = userAnswersStore()

const selectedTestKinds = computed(() => {
  return selectedTests.value.map((test) => {
    return {
      testKind: testKinds.value.find((tk) => tk.id === test.test_kind)!,
      test,
    }
  })
})

function getLine(q: ClientQuestionSchema | ConsultantQuestionSchema, kind = 'client'): string {
  const label = q.label || q.question_text
  const answers =
    'client' == kind ? mapAnswersForClientQuestion(q.id!) : mapAnswersForConsultantQuestion(q.id!)
  return `${label}: ` + answers.map((a) => a.text).join(', ')
}

function copyAnswersToClipboard() {
  let text = ''
  for (const section of answerStore.schema?.sections || []) {
    for (const question of section.client_questions) {
      if (!question.copy_paste) continue
      text += getLine(question, 'client') + '\n'
    }
  }

  for (const question of consultantQuestionnaire?.value?.consultant_questions || []) {
    if (!question.copy_paste) continue
    text += getLine(question, 'consultant') + '\n'
  }

  copy(text).then(() => {
    toast.add({
      severity: 'success',
      summary: 'Copied to clipboard',
      detail: 'Answers copied to clipboard',
      life: 3000,
    })
  })
}

function onBack() {
  router.push({ name: 'consultant-tests', params: { caseId: visit.value?.case } })
}

function onNext() {
  router.push({ name: 'consultant-results', params: { caseId: visit.value?.case } })
}
</script>
<template>
  <section v-if="answerStore.schema && clientAnswers !== null">
    <header class="case">
      <h2>Client Questionnaire</h2>
      <Button
        :icon="showClient ? 'pi pi-eye-slash' : 'pi pi-eye'"
        size="small"
        severity="secondary"
        @click="showClient = !showClient"
        title="Expand Client sections"
      />
    </header>
    <template v-if="showClient">
      <div v-for="section in answerStore.schema.sections" :key="section.id!" class="section">
        <ConsultantSection :section="section" :disable-edit="true" />
      </div>
    </template>

    <header>
      <h2>Consultant</h2>
      <Button
        :icon="showConsultant ? 'pi pi-eye-slash' : 'pi pi-eye'"
        size="small"
        severity="secondary"
        @click="showConsultant = !showConsultant"
        title="Expand Consultant questions"
      />
    </header>
    <section v-if="showConsultant">
      <div
        v-for="question in consultantQuestionnaire?.consultant_questions"
        :key="question.id!"
        class="consultation-question"
      >
        <h3>{{ question.question_text }}</h3>
        <div v-for="answer in mapAnswersForConsultantQuestion(question.id!)" :key="answer.id">
          {{ answer.text }}
        </div>
      </div>
      <h3>Tags</h3>
      <div class="tags">
        <Tag v-for="tag in visit?.tags || []" :key="tag" :value="tag" severity="secondary" />
      </div>
    </section>
    <section>
      <h3>Selected Tests</h3>
      <div v-for="test in selectedTestKinds" :key="test.testKind.id!" class="selected-test">
        <span>
          {{ test.testKind.name }}
        </span>
        <span
          class="test-result"
          :style="
            '--test-color: ' +
            (test.testKind.result_options.find((r) => r.label === test.test.results[0]?.label)
              ?.color || '#aaa')
          "
        >
          {{
            test.test.results.sort((a, b) => -a.created_at.localeCompare(b.created_at)).at(0)
              ?.label || 'no result'
          }}
        </span>
      </div>
      <div v-for="test in freeFormTests" :key="test.id!" class="selected-test">
        <span>
          {{ test.name }}
        </span>
        <span class="test-result" :style="'--test-color: #aaa'">
          {{ test.result || 'no result' }}
        </span>
      </div>
    </section>
    <section class="copy-summary">
      <Button
        icon="pi pi-copy"
        label="Copy to clipboard"
        severity="primary"
        @click="copyAnswersToClipboard"
      />
    </section>
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
  gap: 0.3rem;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0;
}
h3 {
  margin-bottom: 0.3rem;
  margin-top: 0.9rem;
}
.tags {
  display: flex;
  gap: 0.5rem;
}
section {
  margin-bottom: 1rem;
}
.selected-test {
  margin-bottom: 0.5rem;
  display: flex;
  justify-content: space-between;
}
.test-result {
  font-weight: bold;
  background-color: var(--test-color);
  padding: 0.2rem 0.5rem;
  border-radius: 0.3rem;
  color: white;
}
</style>
