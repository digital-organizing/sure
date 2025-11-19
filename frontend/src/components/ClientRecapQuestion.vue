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
  <div>
    <div>{{ props.index }}.</div>
    <div>
      {{ question.question_text }}
    </div>
    <div>
      {{ selectedChoiceText || 'No answer' }}
    </div>
  </div>
</template>
