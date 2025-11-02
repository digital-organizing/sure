<script setup lang="ts">
import { defineProps } from 'vue'
import { type ClientAnswerSchema, type ClientQuestionSchema } from '@/client'
import { Form } from '@primevue/forms'
import { Select } from 'primevue'

const props = defineProps<{
  question: ClientQuestionSchema
}>()

function getClientAnswer(): ClientAnswerSchema {
  // TODO: Implement logic to gather user's answer based on question format
  return {
    question: props.question.id!,
    choices: [],
    texts: [],
    created_at: new Date().toISOString(),
    user: null,
  }
}

defineExpose({
  getClientAnswer,
})
</script>

<template>
  <Form class="client-question">
    <p>{{ props.question.question_text }}</p>
    <template v-if="props.question.format == 'single choice'">
      <div
        v-for="(option, index) in props.question.options"
        :key="index"
        :class="{ 'option-item': true }"
      >
        <RadioButton
          :value="option"
          :inputId="'' + option.id"
          :name="`question-${props.question.id}`"
        />
        <label :for="'' + option.id">
          {{ option.text }}
        </label>
        <Select
          v-if="option.choices && option.choices.length"
          filter
          :options="option.choices"
          :placeholder="'Select an option for ' + option.text"
        />
      </div>
    </template>
    <template v-else-if="props.question.format == 'multiple choice'">
      <div
        v-for="(option, index) in props.question.options"
        :key="index"
        :class="{ 'option-item': true }"
      >
        <Checkbox
          :value="option"
          :inputId="'' + option.id"
          :name="`question-${props.question.id}`"
        />
        <label :for="'' + option.id">
          {{ option.text }}
        </label>
      </div>
    </template>
    <template v-else-if="props.question.format == 'multiple choice + open text field'">
      <div
        v-for="(option, index) in props.question.options"
        :key="index"
        :class="{ 'option-item': true }"
      >
        <Checkbox
          :value="option"
          :inputId="'' + option.id"
          :name="`question-${props.question.id}`"
        />
        <label :for="'' + option.id">
          {{ option.text }}
        </label>
        <InputText type="text" :id="'other-' + props.question.id" v-if="option.allow_text" />
      </div>
    </template>
    <template v-else-if="props.question.format == 'single choice + open text field'">
      <div
        v-for="(option, index) in props.question.options"
        :key="index"
        :class="{ 'option-item': true }"
      >
        <RadioButton
          :value="option"
          :inputId="'' + option.id"
          :name="`question-${props.question.id}`"
        />
        <label :for="'' + option.id">
          {{ option.text }}
        </label>
        <InputText type="text" :id="'other-' + props.question.id" v-if="option.allow_text" />
      </div>
    </template>
    <template v-else-if="props.question.format == 'open text field'">
      <InputText type="text" />
    </template>
  </Form>
</template>
