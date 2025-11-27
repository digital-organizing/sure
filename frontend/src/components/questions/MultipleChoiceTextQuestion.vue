<script setup lang="ts">
import { computed, type ComputedRef } from 'vue'
import { Checkbox, InputText } from 'primevue'
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

const { answer, updateAnswer } = useQuestionAnswer(props.question, props.remote, props.consultant)
const { formatText: f } = useTexts()
function additionalTextPlaceholder(optionText: string) {
  return f('client-question-additional-text-placeholder', [{ key: 'option', value: optionText }])
}
const selectedChoices = computed<string[]>({
  get() {
    return [...answer.value.choices.map((choice) => choice.code)]
  },
  set(newChoices: string[]) {
    const texts = newChoices.map((choiceId) => {
      const option = props.question.options?.find((opt) => opt.code === choiceId)

      // Use custom text if option allows it and text is provided
      if (option?.allow_text && textInputs.value[choiceId]) {
        return textInputs.value[choiceId]
      }

      if (option?.allow_text) return ''

      return option?.text || ''
    })

    updateAnswer(newChoices, texts)
  },
})

const textInputs = computed<Record<string, string>>({
  get() {
    const texts: Record<string, string> = {}
    if (answer.value.choices && answer.value.choices.length > 0) {
      selectedChoices.value.forEach((choiceId, index) => {
        const option = props.question.options?.find((opt) => opt.code === choiceId)
        if (option?.allow_text && answer.value.choices[index].text) {
          texts[choiceId] = answer.value.choices[index].text
        }
      })
    }
    return texts
  },
  set(newTexts: Record<string, string>) {
    const texts = selectedChoices.value.map((choiceId) => {
      const option = props.question.options?.find((opt) => opt.code === choiceId)

      // Use custom text if option allows it and text is provided
      if (option?.allow_text) {
        return newTexts[choiceId] || ''
      }

      return option?.text || ''
    })

    updateAnswer(selectedChoices.value, texts)
  },
})

function triggerTextUpdate() {
  // Trigger the computed setters to update the answer
  textInputs.value = textInputs.value
}

function getAnswer() {
  return answer.value
}

defineExpose({
  getAnswer,
})
</script>

<template>
  <div class="multiple-choice-text-question">
    <div
      v-for="option in question.options"
      :key="option.id || 0"
      class="client-option-item"
      :class="{
        'with-text-input': option.allow_text,
        active: selectedChoices.includes(option.code),
      }"
    >
      <Checkbox
        v-model="selectedChoices"
        :value="option.code"
        :inputId="`option-${option.id}`"
        :name="`question-${question.id}`"
      />
      <label :for="`option-${option.id}`" class="client-option-label">
        {{ option.text }}
      </label>
      <InputText
        v-if="option.allow_text && selectedChoices.includes(option.code!)"
        v-model="textInputs[option.code!]"
        type="text"
        @input="triggerTextUpdate()"
        :placeholder="additionalTextPlaceholder(option.text || '')"
        class="text-input"
      />
    </div>
  </div>
</template>
