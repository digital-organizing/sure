<script lang="ts" setup>
import CaseNoteComponent from '@/components/CaseNoteComponent.vue'
import DocumentUploadComponent from '@/components/DocumentUploadComponent.vue'
import { useCase } from '@/composables/useCase'
import { useTests } from '@/composables/useTests'
import { useTexts } from '@/composables/useTexts'
import { useConfirm } from 'primevue/useconfirm'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{ caseId: string }>()

const router = useRouter()
const confirm = useConfirm()
const { getText: t, formatText: f } = useTexts()

const { onCaseId, updateCaseTestResults, selectedTests, freeFormTests } = useCase()

const { testCategories } = useTests()

const results = ref<{ [id: string]: string | null }>({})
const notes = ref<{ [id: string]: string }>({})
const freeFormResults = ref<{ [id: string]: string }>({})
const showError = ref(false)

onMounted(() => {
  onCaseId(() => {
    selectedTestKinds.value.forEach((test) => {
      const latest = test.test.results
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
        .at(0)
      if (!latest || !test.testKind) {
        return
      }
      const option = test.testKind.result_options.find(
        (option) => option.id == latest.result_option,
      )
      results.value[test.testKind.number] = option?.label || null
      notes.value[test.testKind.number] = latest.note || ''
    })
    freeFormTests.value.forEach((test) => {
      freeFormResults.value[test.id!] = test.result || ''
    })
  })
})

const selectedTestKinds = computed(() => {
  return selectedTests.value
    .map((test) => {
      return {
        testKind: test.test_kind,
        test,
      }
    })
    .filter((tk) => tk.testKind !== undefined) as {
    testKind: (typeof selectedTests.value)[number]['test_kind']
    test: (typeof selectedTests.value)[number]
  }[]
})

const missingResults = computed(() => {
  return selectedTestKinds.value
    .filter((tk) => {
      if (!tk.testKind) {
        return false
      }
      return results.value[tk.testKind.number] == null
    })
    .map((tk) => {
      return tk.testKind?.name || 'Unknown Test'
    })
    .concat(
      freeFormTests.value
        .filter((test) => {
          return !freeFormResults.value[test.id!]
        })
        .map((test) => test.name),
    )
})

const categoryIterator = computed(() => {
  return testCategories.value
    .map((category) => {
      return {
        category,
        tests: selectedTestKinds.value.filter((tk) =>
          category.test_kinds.some((tk2) => tk2.id === tk.testKind.id!),
        ),
      }
    })
    .filter((cat) => cat.tests.length > 0)
})

const colorProperties = [
  '--p-radiobutton-icon-checked-color',
  '--p-radiobutton-icon-checked-hover-color',
  '--p-radiobutton-checked-border-color',
  '--p-radiobutton-checked-hover-border-color',
]

function styleForOption(optionColor: string) {
  return colorProperties.map((prop) => `${prop}: ${optionColor};`).join(' ')
}
const confirmMissing = () => {
  confirm.require({
    message: `There are ${missingResults.value.length} tests without results. Are you sure you want to proceed without completing all test results?`,
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Cancel',
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: 'Save',
    },
    accept: () => {
      submitResults()
    },
    reject: () => {
      showError.value = true
    },
  })
}

function onSaveResults() {
  if (missingResults.value.length > 0) {
    confirmMissing()
  } else {
    submitResults()
  }
}

function submitResults() {
  updateCaseTestResults(results.value, notes.value, freeFormResults.value).then(() => {
    router.push({ name: 'consultant-communication', params: { caseId: props.caseId } })
  })
}
function onBack() {
  router.push({ name: 'consultant-case-summary', params: { caseId: props.caseId } })
}
</script>

<template>
  <header class="case">
    <h2>{{ t('test-results') }}</h2>
  </header>
  <Message v-if="categoryIterator.length == 0" severity="info">
    {{ t('no-tests-selected') }}
  </Message>
  <div
    v-for="category in categoryIterator"
    :key="category.category.id!"
    class="test-category"
    :class="{ error: showError }"
  >
    <h3>
      {{ category.category.name }}
    </h3>
    <div
      v-for="test in category.tests"
      :key="test.testKind.id!"
      class="test"
      :class="results[test.testKind.number!] ? 'done' : 'missing'"
    >
      <h4>
        {{ test.testKind.name }}
      </h4>
      <div class="input">
        <div v-if="test.testKind.interpretation_needed" class="note">
          <InputGroup>
            <InputText v-model="notes[test.testKind.number]" class="note-input" />
            <InputGroupAddon>
              {{ test.testKind.note }}
            </InputGroupAddon>
          </InputGroup>
        </div>
        <div
          v-for="option in test.testKind.result_options.sort((a, b) =>
            a.label.localeCompare(b.label),
          )"
          class="option-item"
          :key="option.id!"
        >
          <RadioButton
            :style="styleForOption(option.color || '#000')"
            :name="'' + test.testKind.id"
            :value="option.label"
            v-model="results[test.testKind.number!]"
            :input-id="'' + option.id!"
          />
          <label :for="'' + option.id!">{{ option.label }}</label>
        </div>
      </div>
    </div>
  </div>
  <div class="text-category" v-if="freeFormTests.length > 0" :class="{ error: showError }">
    <h3>{{ t('free-form-tests') }}</h3>
    <div v-for="test in freeFormTests" :key="test.id!" class="test-category">
      <div class="test" :class="freeFormResults[test.id!] ? 'done' : 'missing'">
        <h4>{{ test.name }}</h4>
        <div class="input">
          <InputText v-model="freeFormResults[test.id!]" :placeholder="t('enter-result').value" />
        </div>
      </div>
    </div>
  </div>
  <div class="missing-warning" v-if="missingResults.length > 0">
    <Message v-if="missingResults.length > 0" severity="warn" icon="pi pi-exclamation-triangle">
      {{ f('missing-results-info', [{ key: 'total', value: '' + missingResults.length }]) }}
      <ul>
        <li v-for="test in missingResults" :key="test!">
          {{ test }}
        </li>
      </ul>
    </Message>
  </div>
  <div class="row save"></div>
  <div class="row">
    <DocumentUploadComponent />
  </div>
  <CaseNoteComponent class="row" />
  <section class="case-footer">
    <Button :label="t('back').value" severity="secondary" @click="onBack()" />

    <Button @click="onSaveResults">{{ t('save-results') }}</Button>
  </section>
</template>

<style scoped>
.test {
  display: flex;
  justify-content: space-between;
  padding-left: 2.5rem;
  padding-right: 1rem;
  gap: 1rem;
  min-height: 45px;
}
.missing-warning {
  margin-top: 1rem;
}

.input {
  display: flex;
  align-items: center;
  gap: 1rem;
  justify-content: flex-end;
}

.note-input {
  text-align: right;
}

.save {
  display: flex;
  justify-content: flex-end;
}

.p-inputgroup {
  max-width: 18rem;
}

.option-item {
  display: inline-flex;
  align-items: center;
  margin-bottom: 0;
  gap: 0.3rem;
}

.test-category {
  margin-bottom: 0rem;
}

.error .missing {
  background-color: var(--p-message-warn-background);
}

h4 {
  margin: 0;
}

.test-category {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

@media screen and (max-width: 1000px) {
  .test {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.3rem;
    margin-bottom: 0.5rem;
  }

  .note {
    width: 100%;
  }

  .input {
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
}

.row {
  margin-top: 1rem;
}
</style>
