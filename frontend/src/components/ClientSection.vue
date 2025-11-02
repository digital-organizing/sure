<script setup lang="ts">
import { type SectionSchema } from '@/client'
import ClientQuestion from './ClientQuestion.vue'
import { userAnswersStore } from '@/stores/answers'
import { ref } from 'vue'

const props = defineProps<{ section: SectionSchema; hasNext: boolean; hasPrevious: boolean }>()

const answersStore = userAnswersStore()
const questions = ref<(typeof ClientQuestion)[]>([])

const emits = defineEmits<{
  (e: 'next'): void
  (e: 'previous'): void
  (e: 'submit'): void
}>()

function onNext() {
  const answers = questions.value.map((q) => q.getClientAnswer())
  answersStore.setAnswersForSection(props.section.id!, answers)
  emits('next')
}

function onPrevious() {
  emits('previous')
}

function onSubmit() {
  emits('submit')
}
</script>

<template>
  <div class="client-section">
    <h2>{{ props.section.title }}</h2>
    <p>{{ props.section.description }}</p>
    <ClientQuestion
      v-for="question in props.section.client_questions"
      :key="question.id!"
      :question="question"
      ref="questions"
    />
    <div class="btn-group">
      <Button
        id="previous"
        v-if="props.hasPrevious"
        label="Previous"
        @click="onPrevious"
        severity="secondary"
        variant="outlined"
        rounded
      />
      <Button
        id="next"
        v-if="props.hasNext"
        label="Next"
        @click="onNext"
        severity="primary"
        rounded
      />
      <Button
        id="submit"
        v-if="!props.hasNext"
        type="submit"
        label="Submit"
        @click="onSubmit"
        severity="primary"
        rounded
      />
    </div>
  </div>
</template>

<style scoped>
.btn-group {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}

#next {
  align-self: flex-end;
  margin-left: auto;
}
</style>
