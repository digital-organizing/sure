<script setup lang="ts">
import type { SectionSchema } from '@/client'
import { computed, ref } from 'vue'
import ClientRecapQuestion from './ClientRecapQuestion.vue'
import ClientQuestion from './ClientQuestion.vue'
import { userAnswersStore } from '@/stores/answers'
import { useTexts } from '@/composables/useTexts'

const props = defineProps<{
  section: SectionSchema
  sectionIndex: number
}>()

const emits = defineEmits<{
  (e: 'edit-section', index: number): void
}>()

const { getText: t } = useTexts()

const answersStore = userAnswersStore()
const questions = ref<(typeof ClientQuestion)[]>([])

const visibleQuestions = computed(() => {
  return props.section.client_questions.filter((q) => {
    if (!q.show_for_options || q.show_for_options.length === 0) {
      return true
    }
    for (const option of q.show_for_options) {
      if (answersStore.isOptionSelected(option)) {
        return true
      }
    }
    return false
  })
})
</script>

<template>
  <div class="client-section-element">
    <div class="client-recap-section-header">
      <p class="client-recap-section-title">{{ props.section.title }}</p>
      <Button
        class="client-recap-edit-button"
        severity="secondary"
        variant="outlined"
        rounded
        @click="emits('edit-section', props.sectionIndex)"
      >
        {{ t('client-recap-edit-button') }}
      </Button>
    </div>
    <ClientRecapQuestion
      v-for="(question, index) in visibleQuestions"
      :key="question.id!"
      :question="question"
      :index="index"
      ref="questions"
    />
  </div>
</template>

<style scoped>
.client-recap-section-header {
  display: flex;
  width: auto;
  justify-content: space-between;
  align-items: center;
  flex-direction: row;
}

.client-recap-section-title {
  color: #000;
  text-align: center;
  font-family: 'Circular Std';
  font-size: 18px;
  font-style: normal;
  font-weight: 700;
  line-height: 42.14px; /* 234.111% */
  margin: 0;
}
.client-recap-edit-button {
  height: 21px;
  border-color: var(--color-ahs-black) !important;
  color: var(--color-ahs-black) !important;
  padding-inline-start: 8px;
  padding-inline-end: 8px;
}
</style>
