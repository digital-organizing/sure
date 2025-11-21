<script setup lang="ts">
import { sureApiGetCaseTests, type TestBundleSchema } from '@/client'
import { useCase } from '@/composables/useCase'
import { useTests } from '@/composables/useTests'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{ caseId: string }>()
const router = useRouter()

const { testKinds, testCategories, testBundles } = useTests()
const { updateCaseTests, error } = useCase()

const selectedTests = ref<number[]>([])

onMounted(() => {
  sureApiGetCaseTests({ path: { pk: props.caseId } }).then((response) => {
    if (Array.isArray(response.data)) {
      selectedTests.value = response.data.map((test) => test.test_kind)
    }
  })
})

function isBundleSelected(bundle: TestBundleSchema) {
  return testKinds.value
    .filter((test) => test.test_bundles.some((b) => b.id === bundle.id))
    .every((test) => selectedTests.value.includes(test.id!))
}

const seletectedBundles = computed({
  get() {
    return testBundles.value
      .filter((bundle) => isBundleSelected(bundle))
      .map((bundle) => bundle.id!)
  },
  set: (newValue: number[]) => {
    const oldSelection = seletectedBundles.value

    testBundles.value.forEach((bundle) => {
      if (newValue.includes(bundle.id!)) {
        selectBundle(bundle.id!)
      } else if (oldSelection.includes(bundle.id!)) {
        deselectBundle(bundle.id!)
      }
    })
  },
})

function deselectBundle(id: number) {
  selectedTests.value = selectedTests.value.filter((testId) => {
    const test = testKinds.value.find((t) => t.id === testId)!
    if (test.test_bundles.some((bundle) => bundle.id === id)) {
      return false
    }
    return true
  })
}

function selectBundle(id: number) {
  selectedTests.value = testKinds.value
    .filter((test) => {
      if (selectedTests.value.includes(test.id!)) {
        return true
      }
      if (test.test_bundles.some((bundle) => bundle.id === id)) {
        return true
      }
      return false
    })
    .map((test) => test.id!)
}

async function submitSelectedTests() {
  await updateCaseTests([...selectedTests.value])
  router.push({ name: 'consultant-case-summary', params: { caseId: props.caseId } })
}
</script>
<template>
  <header>
    <h2>Select Tests to be Performed</h2>
    <Button
      icon="pi pi-eraser"
      label="Clear Selection"
      class="mb-4"
      @click="selectedTests = []"
      severity="secondary"
    />
  </header>
  <Message v-if="error" severity="error" :text="error" />
  <div v-for="bundle in testBundles" :key="bundle.id!" class="test option-item">
    <Checkbox v-model="seletectedBundles" :value="bundle.id!" :input-id="'bundle_' + bundle.id" />

    <label class="ml-2" :for="'bundle_' + bundle.id">{{ bundle.name }}</label>
  </div>
  <div v-for="category in testCategories" :key="category.id!" class="test-category">
    <h3>
      <span class="nr">{{ category.number }}</span
      >{{ category.name }}
    </h3>
    <div v-for="test in category.test_kinds" :key="test.id!" class="test option-item">
      <Checkbox v-model="selectedTests" :value="test.id!" :input-id="'test_' + test.id" />
      <label class="ml-2" :for="'test_' + test.id">{{ test.name }}</label>
    </div>
  </div>
  <section class="case-footer">
    <Button
      label="Back"
      severity="secondary"
      @click="router.push({ name: 'consultant-questionnaire', params: { caseId: props.caseId } })"
    />
    <Button
      :label="`Save ${selectedTests.length} Selected Tests`"
      class="mt-4"
      @click="submitSelectedTests"
    />
  </section>
</template>

<style scoped>
.test {
  margin-left: 2.5rem;
}
header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1rem;
  margin-top: 1em;
}
h2 {
  margin-top: 0;
}
.test-category {
  margin-bottom: 1.5rem;
}
</style>
