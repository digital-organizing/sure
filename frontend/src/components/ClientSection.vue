<script setup lang="ts">
import { type SectionSchema } from '@/client'
import ClientQuestion from './ClientQuestion.vue'
import { userAnswersStore } from '@/stores/answers'
import { computed, ref, useTemplateRef, watch } from 'vue'
import ClientBottomNavButtons from './ClientBottomNavButtons.vue'
import { useElementVisibility } from '@vueuse/core'

const props = defineProps<{ section: SectionSchema; hasNext: boolean; hasPrevious: boolean }>()

const answersStore = userAnswersStore()
const questions = ref<(typeof ClientQuestion)[]>([])
const bottomSpacer = useTemplateRef('bottomSpacer')
const bottomVisible = useElementVisibility(bottomSpacer, {
  rootMargin: '0px 0px -90px 0px',
})

const emits = defineEmits<{
  (e: 'next'): void
  (e: 'previous'): void
  (e: 'submit'): void
}>()

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

const bottomWasVisible = ref<boolean>(false)
watch(bottomVisible, () => {
  bottomWasVisible.value = bottomVisible.value || bottomWasVisible.value
})
watch(props, () => {
  setTimeout(() => {
    bottomWasVisible.value = bottomVisible.value
  }, 200)
})
</script>

<template>
  <div class="client-section-element">
    <p class="section-description">{{ props.section.description }}</p>
    <ClientQuestion
      v-for="(question, index) in visibleQuestions"
      :key="question.id!"
      :question="question"
      :index="index"
      ref="questions"
      :hide-title="false"
    />
    <div class="bottom-spacer" ref="bottomSpacer"></div>
    <div class="client-bottom-button-section">
      <ClientBottomNavButtons
        @next="emits('next')"
        @previous="emits('previous')"
        @submit="emits('submit')"
        :section="props.section"
        :hasNext="props.hasNext"
        :hasPrevious="props.hasPrevious"
        :active="bottomWasVisible"
        ref="questions"
      />
    </div>
  </div>
</template>

<style scoped>
#next {
  align-self: flex-end;
  margin-left: auto;
}

#previous {
  height: 28.5px;
}

.section-description {
  color: var(--color-ahs-black);
  font-family: 'Circular Std';
  font-size: 18px;
  font-style: normal;
  font-weight: 450;
  line-height: 24.5px;
  margin-top: 0px;
}
</style>
