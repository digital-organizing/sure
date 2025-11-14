<script lang="ts" setup>
import type { TagSchema } from '@/client'
import ConsultantQuestion from '@/components/ConsultantQuestion.vue'
import { useCase } from '@/composables/useCase'
import { useTags } from '@/composables/useTags'
import { consultantAnswersStore } from '@/stores/answers'
import { Button } from 'primevue'
import { onMounted, ref } from 'vue'

const {
  onCaseId,
  loading,
  fetchConsultantAnswers,
  fetchConsultantSchema,
  consultantQuestionnaire,
  answerForConsultantQuestion,
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

  fetchVisitDetails().then(() => {
    fetchConsultantAnswers()
  })
}
</script>

<template>
  <div v-if="loading">Loading consultant questionnaire...</div>
  {{ visit?.last_modified_at }}
  <div>
    Consultant Questionnaire Content
    <div v-for="question in consultantQuestionnaire?.consultant_questions" :key="question.id!">
      <h3>{{ question.question_text }}</h3>
      <ConsultantQuestion
        :question="question"
      />
    </div>
    <div>
      <label for="tag-select">Select Tags:</label>
      <MultiSelect
        v-model="selectedTags"
        :options="tags"
        option-label="name"
        option-value=""
        placeholder="Select Tags"
        :show-toggle-all="false"
      />
    </div>
    <Button label="Submit All Answers" @click="onSubmit()" />
  </div>
</template>
