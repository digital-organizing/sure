<script lang="ts" setup>
import type { TagSchema } from '@/client'
import ConsultantQuestion from '@/components/ConsultantQuestion.vue'
import { useCase } from '@/composables/useCase'
import { useTags } from '@/composables/useTags'
import { consultantAnswersStore } from '@/stores/answers'
import { Button } from 'primevue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const {
  onCaseId,
  loading,
  fetchConsultantAnswers,
  consultantQuestionnaire,
  submitConsultantAnswers,
  setCaseTags,
  fetchVisitDetails,
  visit,
} = useCase()

const store = consultantAnswersStore()

const { tags } = useTags()

const selectedTags = ref<TagSchema[]>([])

onMounted(() => {
  onCaseId(() => {
    selectedTags.value = tags.value.filter((tag) => visit.value?.tags.includes(tag.name))
  })
})

async function onSubmit() {
  await Promise.all([
    submitConsultantAnswers(store.answers),
    setCaseTags(selectedTags.value.map((tag) => tag.name)),
  ])

  fetchVisitDetails()
    .then(() => {
      fetchConsultantAnswers()
    })
    .then(() => {
      router.push({ name: 'consultant-tests', params: { caseId: visit?.value?.case } })
    })
}

const nrQuestions = computed(() => {
  return consultantQuestionnaire.value?.consultant_questions.length || 0
})

function onBack() {
  router.push({ name: 'consultant-client-answers', params: { caseId: visit?.value?.case } })
}
</script>

<template>
  <div v-if="loading">Loading consultant questionnaire...</div>
  <div>
    <h2>Consultant Questionnaire Content</h2>

    <Form class="form-col">
      <div
        v-for="(question, idx) in consultantQuestionnaire?.consultant_questions"
        :key="question.id!"
        class="consultation-question"
      >
        <div>
          <h3>
            <span class="nr">{{ idx + 1 }}</span> {{ question.question_text }}
          </h3>
          <ConsultantQuestion :question="question" class="question" />
        </div>
      </div>
      <div>
        <h3>
          <span class="nr">{{ nrQuestions + 2 }}</span
          >Tags
        </h3>
        <MultiSelect
          class="question"
          v-model="selectedTags"
          :options="tags"
          option-label="name"
          option-value=""
          placeholder="Select Tags"
          :show-toggle-all="false"
        />
      </div>
      <footer class="case-footer">
        <Button label="Back" severity="secondary" @click="onBack()" />
        <Button label="Submit All Answers" @click="onSubmit()" />
      </footer>
    </Form>
  </div>
</template>

<style scoped>
h3 {
  display: flex;
  align-items: center;
  gap: 10px;
}
.nr {
  font-weight: bold;
  background-color: var(--color-text);
  color: var(--color-background);
  border-radius: 100%;
  height: 1.5em;
  width: 1.5em;
  display: block;
  text-align: center;
  line-height: 1.5em;
  flex: 0 0 auto;
}
.question {
  margin-left: 2.5em;
}
.form-col {
  align-items: stretch;
}
</style>
