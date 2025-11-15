<script setup lang="ts">
import { computed } from 'vue'
import { Checkbox, InputText } from 'primevue'
import {
  type ClientAnswerSchema,
  type ClientQuestionSchema,
  type ConsultantAnswerSchema,
  type ConsultantQuestionSchema,
} from '@/client'
import { useQuestionAnswer } from '@/composables/useQuestionAnswer'
import type { ComputedRef } from 'vue'

const props = defineProps<{
  question: ClientQuestionSchema | ConsultantQuestionSchema
  remote?: ComputedRef<ClientAnswerSchema | ConsultantAnswerSchema | null>
  consultant?: boolean
}>()

const { answer, updateAnswer } = useQuestionAnswer(props.question, props.remote, props.consultant)
const selectedChoices = computed<string[]>({
  get() {
    const choices: string[] = []
    answer.value.choices.forEach((choice) => {
      if (!choices.includes(choice.code)) {
        choices.push(choice.code)
      }
    })
    return choices
  },
  set(newChoices: string[]) {
    const texts: string[] = []
    const codes: string[] = []

    newChoices.forEach((choiceId) => {
      const option = props.question.options?.find((opt) => opt.code === choiceId)

      // Use custom text if option allows it and text is provided
      if (option?.allow_text && textInputs.value[choiceId]) {
        for (const text of textInputs.value[choiceId]) {
          texts.push(text)
          codes.push(choiceId)
        }
        return
      } else if (option?.allow_text) {
        texts.push('')
        codes.push(choiceId)
      } else {
        texts.push(option?.text || '')
        codes.push(choiceId)
      }
    })

    updateAnswer(codes, texts)
  },
})

const textInputs = computed<Record<string, string[]>>({
  get() {
    const inputs: Record<string, string[]> = {}
    answer.value.choices.forEach((choice, idx) => {
      const option = props.question.options?.find((opt) => opt.code === choice.code)
      if (option?.allow_text) {
        if (inputs[choice.code] === undefined) {
          inputs[choice.code] = []
        }
        inputs[choice.code].push(answer.value.choices[idx].text)
      }
    })
    return inputs
  },
  set(newInputs: Record<string, string[]>) {
    const codes: string[] = []
    const texts: string[] = []

    selectedChoices.value.forEach((choiceId) => {
      const option = props.question.options?.find((opt) => opt.code === choiceId)

      // Use custom text if option allows it and text is provided
      if (option?.allow_text && newInputs[choiceId].length > 0) {
        for (const text of newInputs[choiceId]) {
          texts.push(text)
          codes.push(choiceId)
        }
        return
      }

      texts.push(option?.text || '')
      codes.push(choiceId)
    })

    updateAnswer(codes, texts)
  },
})

function getAnswer() {
  return answer.value
}

function triggerTextUpdate() {
  // Trigger the computed setters to update the answer
  textInputs.value = textInputs.value
}

function addTextField(choiceId: string) {
  const newTextInputs = { ...textInputs.value }
  if (!newTextInputs[choiceId]) {
    newTextInputs[choiceId] = []
  }
  newTextInputs[choiceId].push('')
  textInputs.value = newTextInputs
}

function removeTextField(choiceId: string, index: number) {
  const newTextInputs = { ...textInputs.value }
  if (newTextInputs[choiceId]) {
    newTextInputs[choiceId].splice(index, 1)
    textInputs.value = newTextInputs
  }
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
      <div v-if="option.allow_text && selectedChoices.includes(option.code!)" class="text-inputs">
        <div
          v-for="(textInput, index) in textInputs[option.code!]"
          :key="index"
          class="text-input-wrapper"
        >
          <InputGroup>
            <InputText
              :inputId="`option-${option.id}-text-${index}`"
              v-model="textInputs[option.code!][index]"
              @input="triggerTextUpdate()"
              type="text"
              :placeholder="'Additional text for ' + option.text"
              class="text-input"
            />
            <InputGroupAddon>
              <Button
                icon="pi pi-times"
                severity="secondary"
                @click="removeTextField(option.code, index)"
                :disabled="index == 0"
              />
            </InputGroupAddon>
          </InputGroup>
        </div>
        <Button
          v-if="textInputs[option.code!].at(-1) != '' || textInputs[option.code!].length === 0"
          type="button"
          icon="pi pi-plus"
          iconPos="left"
          label="Add another"
          severity="success"
          @click="addTextField(option.code!)"
          class="add-text-input-button"
        >
        </Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.option-item {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
  gap: 0.5rem;
}
.option-item .text-inputs {
  grid-area: textinput;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>
