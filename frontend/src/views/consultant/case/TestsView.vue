<script setup lang="ts">
import { sureApiGetCaseFreeFormTests, sureApiGetCaseTests } from '@/client'
import { useCase } from '@/composables/useCase'
import { useTests } from '@/composables/useTests'
import { useTexts } from '@/composables/useTexts'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{ caseId: string }>()
const router = useRouter()
const { getText: t, formatText } = useTexts()

const { testKinds, testCategories, testBundles } = useTests()
const { updateCaseTests, error } = useCase()

const selectedTests = ref<number[]>([])

const freeFormTests = ref<string[]>([])

onMounted(() => {
  sureApiGetCaseTests({ path: { pk: props.caseId } }).then((response) => {
    if (Array.isArray(response.data)) {
      selectedTests.value = response.data.map((test) => test.test_kind.id!)
    }
  })
  sureApiGetCaseFreeFormTests({ path: { pk: props.caseId } }).then((response) => {
    if (Array.isArray(response.data)) {
      freeFormTests.value = response.data.map((test) => test.name)
    }
  })
})

const seletectedBundles = ref<number[]>([])

function onBundleChange(e: Event, bundleId: number) {
  if ((e.target as HTMLInputElement)?.checked) {
    selectBundle(bundleId)
  }
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
  await updateCaseTests([...selectedTests.value], [...freeFormTests.value])
  router.push({ name: 'consultant-case-summary', params: { caseId: props.caseId } })
}
</script>
<template>
  <header class="case">
    <h2>{{ t('select-tests') }}</h2>
    <Button
      icon="pi pi-eraser"
      :label="t('clear-selection').value"
      class="mb-4"
      @click="
        () => {
          selectedTests = []
          seletectedBundles = []
        }
      "
      severity="secondary"
    />
  </header>
  <Message v-if="error" severity="error" :text="error" />
  <h3>{{ t('bundles') }}</h3>
  <div v-for="bundle in testBundles" :key="bundle.id!" class="test option-item">
    <Checkbox
      v-model="seletectedBundles"
      @change="onBundleChange($event, bundle.id!)"
      :value="bundle.id!"
      :input-id="'bundle_' + bundle.id"
    />

    <label class="ml-2" :for="'bundle_' + bundle.id">{{ bundle.name }}</label>
  </div>
  <div v-for="category in testCategories" :key="category.id!" class="test-category">
    <h3>
      {{ category.name }}
    </h3>
    <div v-for="test in category.test_kinds" :key="test.id!" class="test option-item">
      <Checkbox v-model="selectedTests" :value="test.id!" :input-id="'test_' + test.id" />
      <label class="ml-2" :for="'test_' + test.id">{{ test.name }}</label>
    </div>
  </div>
  <div class="free-form test">
    <div v-for="(name, idx) in freeFormTests" :key="idx" class="free-form-item">
      <InputGroup>
        <InputText v-model="freeFormTests[idx]" :placeholder="t('enter-custom-test').value" />
        <InputGroupAddon>
          <Button
            icon="pi pi-times"
            class="ml-2"
            @click="freeFormTests.splice(idx, 1)"
            variant="text"
          />
        </InputGroupAddon>
      </InputGroup>
    </div>
    <Button
      icon="pi pi-plus"
      severity="secondary"
      class="mt-2"
      @click="freeFormTests.push('')"
      v-if="freeFormTests.length == 0 || freeFormTests.at(-1)!.length > 0"
    />
  </div>
  <section class="case-footer">
    <Button
      :label="t('back').value"
      severity="secondary"
      @click="router.push({ name: 'consultant-questionnaire', params: { caseId: props.caseId } })"
    />
    <Button
      :label="
        formatText('save-selected-tests', [
          { key: 'count', value: String(selectedTests.length + freeFormTests.length) },
        ]).value
      "
      class="mt-4"
      @click="submitSelectedTests"
    />
  </section>
</template>

<style scoped>
.test {
  margin-left: 2.5rem;
}
.test-category {
  margin-bottom: 1.5rem;
}
.free-form-item {
  margin-bottom: 0.5rem;
}
</style>
