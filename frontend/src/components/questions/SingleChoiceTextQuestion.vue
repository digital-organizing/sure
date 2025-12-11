<script setup lang="ts">
import { computed, type ComputedRef } from 'vue'
import { RadioButton, InputText, Textarea } from 'primevue'
import {
  type ClientAnswerSchema,
  type ClientQuestionSchema,
  type ConsultantAnswerSchema,
  type ConsultantQuestionSchema,
} from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'
import { useTexts } from '@/composables/useTexts'

const props = defineProps<{
  question: ClientQuestionSchema | ConsultantQuestionSchema
  remote?: ComputedRef<ClientAnswerSchema | ConsultantAnswerSchema | null>
  consultant?: boolean
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question)
const { formatText: f } = useTexts()
const selectedChoice = computed<string | null>({
  get() {
    return answer.value.choices[0]?.code || null
  },
  set(newChoice: string | null) {
    if (newChoice !== null) {
      const option = props.question.options?.find((opt) => opt.code === newChoice)

      updateAnswer([newChoice], [option?.allow_text ? '' : option?.text || ''])
    } else {
      updateAnswer([], [])
    }
  },
})

const useTextarea = computed(() => {
  if (props.question.use_textarea !== undefined) {
    return props.question.use_textarea
  }
  return false
})

const text = computed<string>({
  get() {
    return answer.value.choices[0]?.text || ''
  },
  set(newText: string) {
    if (selectedChoice.value !== null) {
      const option = props.question.options?.find((opt) => opt.code === selectedChoice.value)
      updateAnswer([selectedChoice.value], [option?.allow_text ? newText : option?.text || ''])
    } else {
      updateAnswer([], [])
    }
  },
})

function additionalTextPlaceholder(optionText: string) {
  return f('client-question-additional-text-placeholder', [{ key: 'option', value: optionText }])
}

function getAnswer() {
  return answer.value
}

defineExpose({
  getAnswer,
})
</script>

<template>
  <div class="single-choice-text-question">
    <div
      v-for="option in question.options"
      :key="option.id || 0"
      class="client-option-item"
      :class="{ 'with-text-input': option.allow_text, active: selectedChoice === option.code }"
    >
      <RadioButton
        v-model="selectedChoice"
        :value="option.code"
        :inputId="`option-${option.id}`"
        :name="`question-${question.id}`"
      />
      <label :for="`option-${option.id}`" class="client-option-label">
        {{ option.text }}
      </label>
      <template v-if="option.allow_text && selectedChoice === option.code">
        <Textarea
          v-if="useTextarea"
          v-model="text"
          autoResize
          :rows="4"
          :placeholder="additionalTextPlaceholder(option.text || '').value"
          class="text-input consult-wish-textarea"
        />
        <InputText
          v-else
          v-model="text"
          type="text"
          :placeholder="additionalTextPlaceholder(option.text || '').value"
          class="text-input"
        />
      </template>
    </div>
  </div>
</template>

<style scoped>
.consult-wish-textarea {
  min-height: 120px;
}
</style>
