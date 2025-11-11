<script setup lang="ts">
import { ref, watch } from 'vue'
import { Checkbox, InputText } from 'primevue'
import {
  type ClientAnswerSchema,
  type ClientQuestionSchema,
  type ConsultantAnswerSchema,
  type ConsultantQuestionSchema,
} from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'

const props = defineProps<{
  question: ClientQuestionSchema | ConsultantQuestionSchema
  remote?: ClientAnswerSchema | ConsultantAnswerSchema | null
  consultant?: boolean
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question, props.remote, props.consultant)
const selectedChoices = ref<string[]>([])
const textInputs = ref<Record<string, string[]>>({})

if (answer.value.choices && answer.value.choices.length > 0) {
  selectedChoices.value = []
  answer.value.choices.forEach((choice, idx) => {
    if (!selectedChoices.value.includes(choice.code)) {
      selectedChoices.value.push(choice.code)
    }
    const option = props.question.options?.find((opt) => opt.code === choice.code)
    if (option?.allow_text) {
      if (textInputs.value[choice.code] === undefined) {
        textInputs.value[choice.code] = []
      }
      textInputs.value[choice.code].push(answer.value.choices[idx].text)
    }
  })
}

// Update store when selection or text changes
watch(
  [selectedChoices, textInputs, props.remote],
  () => {
    const texts: string[] = []
    const codes: string[] = []

    selectedChoices.value.forEach((choiceId) => {
      const option = props.question.options?.find((opt) => opt.code === choiceId)

      // Use custom text if option allows it and text is provided
      if (option?.allow_text && textInputs.value[choiceId]) {
        for (const text of textInputs.value[choiceId]) {
          texts.push(text)
          codes.push(choiceId)
        }
        return
      }
      if (
        option?.allow_text &&
        (!textInputs.value[choiceId] || textInputs.value[choiceId].length === 0)
      ) {
        textInputs.value[choiceId] = ['']
        return
      }

      texts.push(option?.text || '')
      codes.push(choiceId)
    })

    updateAnswer(codes, texts)
  },
  { deep: true },
)

function getAnswer() {
  return answer.value
}

defineExpose({
  getAnswer,
})
</script>

<template>
  <div class="multiple-choice-multiple-text-question">
    <div
      v-for="option in question.options"
      :key="option.id || 0"
      class="option-item"
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
      <label :for="`option-${option.id}`">
        {{ option.text }}
      </label>
      <template v-if="option.allow_text && selectedChoices.includes(option.code!)">
        <div
          v-for="(textInput, index) in textInputs[option.code!]"
          :key="index"
          class="text-input-wrapper"
        >
          <InputText
            v-model="textInputs[option.code!][index]"
            type="text"
            :placeholder="'Additional text for ' + option.text"
            class="text-input"
          />
          <Button
            v-if="index > 0"
            type="button"
            icon="pi pi-times"
            class="p-button-text p-button-danger delete-text-input-button"
            @click="textInputs[option.code!].splice(index, 1)"
            >Remove</Button
          >
        </div>
        <button
          v-if="textInputs[option.code!].at(-1) != ''"
          type="button"
          @click="textInputs[option.code!] = [...(textInputs[option.code!] || []), '']"
          class="add-text-input-button"
        >
          Add another
        </button>
      </template>
    </div>
  </div>
</template>
