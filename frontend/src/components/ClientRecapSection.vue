<script setup lang="ts">
import type { SectionSchema } from '@/client';
import { computed, ref } from 'vue'
import ClientRecapQuestion from './ClientRecapQuestion.vue';
import ClientQuestion from './ClientQuestion.vue'
import { userAnswersStore } from '@/stores/answers'


const props = defineProps<{
    section: SectionSchema
}>()

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
        <ClientRecapQuestion 
            v-for="question in visibleQuestions"
            :key="question.id!"
            :question="question"
            :index="1"
            ref="questions"
        />
    </div>
</template>