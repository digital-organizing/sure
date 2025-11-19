<script setup lang="ts">
import { sureApiGetCaseQuestionnaire, sureApiSubmitCase, type QuestionnaireSchema } from '@/client'
import ClientSection from '@/components/ClientSection.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import ClientNavigationTop from '@/components/ClientNavigationTop.vue'
import { useScroll } from '@/composables/useScroll'
import { userAnswersStore } from '@/stores/answers'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import ClientRecap from '@/components/ClientRecap.vue'

const formStructure = ref<QuestionnaireSchema | null>(null)
const answersStore = userAnswersStore()
const formIndex = ref<number>(0)
const totalSections = computed(() => formStructure.value?.sections.length ?? 0)
const isRecapStep = computed(() => formIndex.value === totalSections.value)
const currentSectionTitle = computed(() => {
  if (!formStructure.value) {
    return ''
  }
  if (isRecapStep.value) {
    return 'Summary'
  }
  return formStructure.value.sections[formIndex.value]?.title ?? ''
})

const progressValue = computed(() => {
  const total = totalSections.value
  if (total === 0) {
    return 0
  }
  return Math.min(formIndex.value + 1, total)
})

const props = defineProps<{
  caseId: string
}>()

const { scrollToTop } = useScroll()

onMounted(async () => {
  formStructure.value = (await sureApiGetCaseQuestionnaire({ path: { pk: props.caseId } })).data!
  answersStore.setSchema(formStructure.value)

  const savedIndex = localStorage.getItem('clientFormIndex')
  const savedId = localStorage.getItem('clientFormCaseId')
  if (savedId !== props.caseId) {
    localStorage.setItem('clientFormCaseId', props.caseId)
    localStorage.setItem('clientFormIndex', '0')
    formIndex.value = 0
  } else if (savedIndex) {
    formIndex.value = parseInt(savedIndex, 10)
  }
})

watch(formIndex, (newIndex) => {
  localStorage.setItem('clientFormIndex', newIndex.toString())
})

function nextQuestion() {
  if (formIndex.value < totalSections.value) {
    formIndex.value++
    nextTick(() => {
      scrollToTop()
    })
  }
}

function previousQuestion() {
  if (formIndex.value > 0) {
    formIndex.value--
  }
}

function goToSection(index: number) {
  formIndex.value = index
  nextTick(() => {
    scrollToTop()
  })
}

function onSubmit() {
  sureApiSubmitCase({ path: { pk: props.caseId }, body: answersStore.answers })
    .then(() => {
      alert('Form submitted successfully!')
    })
    .catch(() => {
      alert('Error submitting form. Please try again.')
    })
}
</script>

<template>
  <div id="client-form-view">
    <div v-if="formStructure">
      <div id="navi-top" class="client-section-element">
        <ClientNavigationTop
          :section-title="currentSectionTitle"
          :sections="formStructure.sections"
          @select-section="goToSection"
        />
        <ProgressBar :total="formStructure?.sections.length" :value="progressValue" />
      </div>
      <div id="client-sections" v-if="formIndex < (formStructure?.sections.length ?? 0)">
        <ClientSection
          @next="nextQuestion"
          @previous="previousQuestion"
          @submit="onSubmit"
          :section="formStructure?.sections[formIndex]!"
          :has-next="formIndex < (formStructure?.sections.length ?? 0)"
          :has-previous="formIndex > 0"
        />
      </div>
      <div id="client-recap" v-else-if="formIndex === (formStructure?.sections.length ?? 0)">
        <ClientRecap
          @next="nextQuestion"
          @previous="previousQuestion"
          @submit="onSubmit"
          @edit-section="goToSection"
          :has-next="formIndex < (formStructure?.sections.length ?? 0)"
          :has-previous="formIndex > 0"
          :form="formStructure"
          :form-index="formIndex"
        />
      </div>
      <div v-else>
        <p>Phone Number Page</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
#navi-top {
  display: flex;
  width: 100%;
  padding-top: 50px;
  padding-bottom: 30px;
  flex-direction: column;
  align-items: flex-start;
  gap: 20px;
  position: sticky;
  background-color: var(--color-ahs-white);
  z-index: 10;
  top: 0;
}

#client-sections {
  z-index: 5;
}

button {
  margin: 10px;
}
#navi-bottom {
  display: flex;
  justify-content: space-between;
  margin-top: 30px;
}
#client-form-view {
  max-width: 800px;
  margin: auto;
}
</style>
