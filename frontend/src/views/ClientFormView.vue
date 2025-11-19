<script setup lang="ts">
import { sureApiGetQuestionnaire, type QuestionnaireSchema } from '@/client'
import ClientSection from '@/components/ClientSection.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import ClientNavigationTop from '@/components/ClientNavigationTop.vue'
import { useScroll } from '@/composables/useScroll'
import { userAnswersStore } from '@/stores/answers'
import { nextTick, onMounted, ref, watch } from 'vue'
import ClientRecap from '@/components/ClientRecap.vue'

const formStructure = ref<QuestionnaireSchema | null>(null)
const answersStore = userAnswersStore()
const formIndex = ref<number>(0)
const recapActive = ref(false)

const { scrollToTop } = useScroll()

onMounted(async () => {
  formStructure.value = (await sureApiGetQuestionnaire({ path: { pk: 2 } })).data!
  answersStore.setSchema(formStructure.value)

  const savedIndex = localStorage.getItem('clientFormIndex')
  if (savedIndex) {
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

function submitQuestionnaire() {
  recapActive.value = !recapActive.value
}

</script>

<template>
  <div id="client-form-view">
    <div v-if="formStructure">
      <div id="navi-top" class="client-section-element">
        <ClientNavigationTop :sectionTitle="formStructure?.sections[formIndex].title" />
        <ProgressBar :total="formStructure?.sections.length" :value="formIndex + 1" />
      </div>
      <div id="client-sections" v-if="formIndex < (formStructure?.sections.length ?? 0) - 1">
        <ClientSection
          @next="nextQuestion"
          @previous="previousQuestion"
          @submit="submitQuestionnaire"
          :section="formStructure?.sections[formIndex]!"
          :has-next="formIndex < (formStructure?.sections.length ?? 0) - 1 + 2"
          :has-previous="formIndex > 0"
        />
      </div>
      <div id="client-recap" v-else-if="formIndex === (formStructure?.sections.length ?? 0) - 1">
        <ClientRecap
        @next="nextQuestion"
        @previous="previousQuestion"
        @submit="submitQuestionnaire"
        :has-next="formIndex < (formStructure?.sections.length ?? 0) - 1 + 2"
        :has-previous="formIndex > 0"
        :form="formStructure"
        :form-index="formIndex"
        />
      </div>
      <div v-else>
        <p>
          Phone Number Page
        </p>
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
