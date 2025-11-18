<script setup lang="ts">
import { type SectionSchema } from '@/client'
import ClientQuestion from './ClientQuestion.vue'
import { userAnswersStore } from '@/stores/answers'
import { computed, ref } from 'vue'
import IconRightArrow from './icons/IconRightArrow.vue';
import IconLeftArrowSmall from './icons/IconLeftArrowSmall.vue';

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
  <div class="client-section">
    <h2 class="section-title">{{ props.section.title }}</h2>
    <p class="section-description">{{ props.section.description }}</p>
    <ClientQuestion
      v-for="(question, index) in visibleQuestions"
      :key="question.id!"
      :question="question"
      :index="index"
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
        icon="IconLeftArrowSmall"
        rounded
      > <IconLeftArrowSmall/> Previous </Button>
      <Button
        id="next"
        v-if="props.hasNext"
        label="Next"
        @click="onNext"
        severity="primary"
        rounded
      > Next <IconRightArrow /> </Button>
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

.section-title {
  color: #000;
  font-family: "Circular Std";
  font-size: 18px;
  font-style: normal;
  font-weight: 700;
  line-height: 24.5px; /* 136.111% */
  margin-bottom: 0px;
}

.section-description {
  color: #000;
  font-family: "Circular Std";
  font-size: 18px;
  font-style: normal;
  font-weight: 450;
  line-height: 24.5px;
  margin-top: 0px;
}
</style>
