<script lang="ts" setup>
import { sureApiGetCaseTests, type TestSchema } from '@/client'
import { useCase } from '@/composables/useCase'
import { useTests } from '@/composables/useTests'
import { useConfirm } from 'primevue/useconfirm'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{ caseId: string }>()

const router = useRouter()
const confirm = useConfirm()

const { onCaseId, updateCaseTestResults, visit } = useCase()

const { testKinds, testCategories } = useTests()
const selectedTests = ref<TestSchema[]>([])

const results = ref<{ [id: string]: string | null }>({})
const notes = ref<{ [id: string]: string }>({})
const showError = ref(false)

onMounted(() => {
  onCaseId(() => {
    sureApiGetCaseTests({ path: { pk: visit.value!.case } }).then((response) => {
      if (!Array.isArray(response.data)) {
        return
      }
      selectedTests.value = response.data
      selectedTestKinds.value.forEach((test) => {
        const latest = test.test.results
          .sort((a, b) => b.created_at.localeCompare(a.created_at))
          .at(0)
        if (!latest) {
          return
        }
        results.value[test.testKind.number] = latest.label
        notes.value[test.testKind.number] = latest.note || ''
      })
    })
  })
})

const selectedTestKinds = computed(() => {
  return selectedTests.value.map((test) => {
    return {
      testKind: testKinds.value.find((tk) => tk.id === test.test_kind)!,
      test,
    }
  })
})

const missingResults = computed(() => {
  return selectedTestKinds.value.filter((tk) => {
    return results.value[tk.testKind.number!] == null
  })
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
  updateCaseTestResults(results.value, notes.value).then(() => {
    router.push({ name: 'consultant-communication', params: { caseId: props.caseId } })
  })
}
function onBack() {
  router.push({ name: 'consultant-case-summary', params: { caseId: props.caseId } })
}
</script>

<template>
  <header class="case">
    <h2>Test Results</h2>
  </header>
  <Message v-if="categoryIterator.length == 0" severity="info">
    No tests have been selected for this case. Please go back to the test selection and choose tests
    to be performed.
  </Message>
  <div
    v-for="category in categoryIterator"
    :key="category.category.id!"
    class="test-category"
    :class="{ error: showError }"
  >
    <h3>
      <span class="nr">{{ category.category.number }}</span
      >{{ category.category.name }}
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
  <div>
    <Message v-if="missingResults.length > 0" severity="warn" icon="pi pi-exclamation-triangle">
      {{ missingResults.length }} test results are missing. Please provide results for all selected
      tests before proceeding.
      <ul>
        <li v-for="test in missingResults" :key="test.testKind.id!">
          {{ test.testKind.name }}
        </li>
      </ul>
    </Message>
  </div>
  <section class="case-footer">
    <Button label="Back" severity="secondary" @click="onBack()" />
    <Button @click="onSaveResults">Save Results</Button>
  </section>
</template>

<style scoped>
.test {
  display: flex;
  justify-content: space-between;
  padding-left: 2.5rem;
  padding-right: 1rem;
  gap: 1rem;
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
  margin-bottom: 1.5rem;
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
    gap: 1rem;
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
</style>
