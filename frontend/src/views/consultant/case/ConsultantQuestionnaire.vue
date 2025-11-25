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

defineProps<{
  caseId: string
}>()

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
    <header class="case">
      <h2>Consultant Questionnaire Content</h2>
    </header>
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
        <div class="tag-boxes question">
          <div class="option-item" v-for="tag in tags" :key="tag.id!">
          <Checkbox
            :input-id="'tag_' + tag.id!"
            :value="tag"
            v-model="selectedTags"
          />
          <label :for="'tag_' + tag.id!">{{ tag.name }}</label>
          </div>
        </div>
      </div>
      <footer class="case-footer">
        <Button label="Back" severity="secondary" @click="onBack()" />
        <Button label="Submit All Answers" @click="onSubmit()" />
      </footer>
    </Form>
  </div>
</template>

<style scoped>
.question {
  margin-left: 2.5em;
}
.form-col {
  align-items: stretch;
}
</style>
