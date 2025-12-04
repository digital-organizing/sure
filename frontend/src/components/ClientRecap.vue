<script setup lang="ts">
import type { QuestionnaireSchema } from '@/client'
import ClientBottomNavButtons from './ClientBottomNavButtons.vue'

import { defineProps, defineEmits } from 'vue'
import ClientRecapSection from './ClientRecapSection.vue'

const props = defineProps<{
  hasNext: boolean
  hasPrevious: boolean
  form: QuestionnaireSchema
  formIndex: number
}>()

const emits = defineEmits<{
  (e: 'next'): void
  (e: 'previous'): void
  (e: 'submit'): void
  (e: 'edit-section', index: number): void
}>()

// const answersStore = userAnswersStore()
</script>

<template>
  <div class="client-section-element">
    <div>
      <ClientRecapSection
        v-for="(section, index) in props.form.sections"
        :key="section.id ?? index"
        :section="section"
        :section-index="index"
        @edit-section="(targetIndex) => emits('edit-section', targetIndex)"
      />
    </div>
    <div class="client-bottom-button-section">
      <ClientBottomNavButtons
        @next="emits('next')"
        @previous="emits('previous')"
        @submit="emits('submit')"
        :section="props.form.sections[props.formIndex]"
        :has-next="props.hasNext"
        :has-previous="props.hasPrevious"
      />
    </div>
  </div>
</template>
