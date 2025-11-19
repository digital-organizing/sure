<script setup lang="ts">
import { defineProps, computed } from 'vue'
import { type ClientQuestionSchema } from '@/client'
import { userAnswersStore } from '@/stores/answers'

const props = defineProps<{
  question: ClientQuestionSchema
  index: number
}>()

const answersStore = userAnswersStore()

const answer = computed(() => {
  const id = props.question.id
  return id != null ? answersStore.getAnswerForQuestion(id) : null
})

const selectedChoiceText = computed(() => {
  const choices = answer.value?.choices
  return choices && choices.length > 0 ? choices.map((choice) => choice.text).join(', ') : ''
})
</script>

<template>
  <div class="client-recap-question-grid">
    <div class="client-recap-question-text">{{ props.index + 1 }}.</div>
    <div class="client-recap-question-text">
      {{ question.question_text }}
    </div>
    <div></div>
    <div class="client-recap-question-answer">
      {{ selectedChoiceText || 'No answer' }}
    </div>
  </div>
</template>

<style scoped>
.client-recap-question-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-auto-rows: auto;
    column-gap: 8px;
    row-gap: 0px;
    padding-bottom: 8px;
}
.client-recap-question-text {
    color: var(--color-ahs-black);
    font-family: "Circular Std";
    font-size: 15px;
    font-style: normal;
    font-weight: 450;
    line-height: 20px; /* 133.333% */
}
.client-recap-question-answer {
    color: var(--color-ahs-black);
    font-family: "Circular Std";
    font-size: 15px;
    font-style: normal;
    font-weight: 700;
    line-height: 20px; /* 133.333% */
}
</style>
