<script setup lang="ts">
import { userAnswersStore } from '@/stores/answers'
import ClientQuestion from './ClientQuestion.vue'
import { defineProps, defineEmits, ref } from 'vue'
import type { SectionSchema } from '@/client'
import IconLeftArrowSmall from './icons/IconLeftArrowSmall.vue'
import IconRightArrow from './icons/IconRightArrow.vue'
import { useTexts } from '@/composables/useTexts'

const props = defineProps<{
  section: SectionSchema
  hasNext: boolean
  hasPrevious: boolean
}>()

const questions = ref<(typeof ClientQuestion)[]>([])
const answersStore = userAnswersStore()

const emits = defineEmits<{
  (e: 'next'): void
  (e: 'previous'): void
  (e: 'submit'): void
}>()

const { getText: t } = useTexts()

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
  <div class="btn-group">
    <Button
      id="previous"
      v-if="props.hasPrevious"
      @click="onPrevious"
      severity="secondary"
      variant="outlined"
      :label="t('client-form-previous-button').value"
      rounded
      :aria-label="t('client-form-previous-button').value"
    >
      <IconLeftArrowSmall /> {{ t('client-form-previous-button') }}
    </Button>
    <Button
      id="next"
      v-if="props.hasNext"
      @click="onNext"
      severity="primary"
      rounded
      :aria-label="t('client-form-next-button').value"
    >
      {{ t('client-form-next-button') }} <IconRightArrow />
    </Button>
    <Button
      id="submit"
      v-if="!props.hasNext"
      type="submit"
      @click="onSubmit"
      severity="primary"
      rounded
      :aria-label="t('client-form-submit-button').value"
    >
      {{ t('client-form-submit-button') }}
    </Button>
  </div>
</template>

<style scoped>
.btn-group {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-top: 20px;
  background-color: var(--color-ahs-white);
  padding-bottom: 30px;
  padding-top: 15px;
}

#next {
  align-self: flex-end;
  margin-left: auto;
}

#previous {
  height: 28.5px;
  padding: 5.25px 8.75px;
}

#submit {
  align-self: flex-end;
  margin-left: auto;
}
</style>
