<script setup lang="ts">
import { sureApiGetCaseQuestionnaire, sureApiSubmitCase, type QuestionnaireSchema } from '@/client'
import ClientSection from '@/components/ClientSection.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import { useScroll } from '@/composables/useScroll'
import { userAnswersStore } from '@/stores/answers'
import { nextTick, onMounted, ref, watch } from 'vue'

const formStructure = ref<QuestionnaireSchema | null>(null)
const answersStore = userAnswersStore()
const formIndex = ref<number>(0)

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
  console.log('Resetting form index for new case')
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
  if (formIndex.value < (formStructure.value?.sections.length ?? 0) - 1) {
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
    <div id="nav-bar">Navbar</div>
    <div v-if="formStructure">
      <h1>Client Form</h1>
      <ProgressBar :total="formStructure?.sections.length" :value="formIndex + 1" />
      <ClientSection
        @next="nextQuestion"
        @previous="previousQuestion"
        @submit="onSubmit"
        :section="formStructure?.sections[formIndex]!"
        :has-next="formIndex < (formStructure?.sections.length ?? 0) - 1"
        :has-previous="formIndex > 0"
      />
      <pre v-if="formIndex == formStructure?.sections.length - 1">
        {{ answersStore.answers }}
      </pre>
    </div>
  </div>
</template>

<style scoped>
div {
  margin: 20px;
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
