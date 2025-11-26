<script setup lang="ts">
import { sureApiGetCaseQuestionnaire, sureApiSubmitCase, type QuestionnaireSchema } from '@/client'
import ClientSection from '@/components/ClientSection.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import ClientNavigationTop from '@/components/ClientNavigationTop.vue'
import { useScroll } from '@/composables/useScroll'
import { userAnswersStore } from '@/stores/answers'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ClientRecap from '@/components/ClientRecap.vue'
import { useTexts } from '@/composables/useTexts'

const formStructure = ref<QuestionnaireSchema | null>(null)
const answersStore = userAnswersStore()
const formIndex = ref<number>(0)
const totalSections = computed(() => formStructure.value?.sections.length ?? 0)
const isRecapStep = computed(() => formIndex.value === totalSections.value)
const error = ref<string | null>(null)
const { getText: t } = useTexts()
const currentSectionTitle = computed(() => {
  if (!formStructure.value) {
    return ''
  }
  if (isRecapStep.value) {
    return t('client-form-summary-title').value
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
const router = useRouter()

onMounted(async () => {
  const response = await sureApiGetCaseQuestionnaire({ path: { pk: props.caseId } })
  if (response.response.status === 302) {
    router.push(`/client/${props.caseId}/phone`)
    return
  }
  if (response.error && response.error.message) {
    error.value = Array.isArray(response.error.message)
      ? response.error.message.join(', ')
      : response.error.message
    return
  }
  formStructure.value = response.data!
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
      router.push(`/client/${props.caseId}/phone`)
    })
    .catch(() => {
      alert(t('client-form-submit-error-alert').value)
    })
}
</script>

<template>
  <div class="client-form-view">
    <Message class="form-error" severity="error" v-if="error"
      ><strong>{{ t('client-form-error-label') }}</strong> {{ error }}</Message
    >
    <div v-if="formStructure">
      <div id="navi-top" class="client-section-element">
        <ClientNavigationTop
          :section-title="currentSectionTitle"
          :sections="formStructure.sections"
          :language-selector-only="false"
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
.form-error {
  margin-top: 1rem;
}
</style>
