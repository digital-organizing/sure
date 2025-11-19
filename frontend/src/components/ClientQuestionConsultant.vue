<script lang="ts" setup>
import type { AnswerSchema, ClientQuestionSchema } from '@/client'
import { useCase } from '@/composables/useCase'
import ClientQuestion from './ClientQuestion.vue'
import { computed, ref } from 'vue'

const props = defineProps<{
  question: ClientQuestionSchema
  disableEdit?: boolean
}>()

const questionComponentRef = ref<{ getClientAnswer: () => AnswerSchema } | null>(null)

const edit = ref(false)

const show = ref(true)

const allowEdit = computed(() => {
  if (props.disableEdit === undefined) {
    return true
  }
  return !props.disableEdit
})

const { answerForClientQuestion, submitClientAnswer, fetchVisitDetails } = useCase()

function onSubmit() {
  if (questionComponentRef.value) {
    const answer = questionComponentRef.value.getClientAnswer()
    submitClientAnswer(answer).then(() => {
      fetchVisitDetails()
    })
    edit.value = false
  }
}

function getAnswer(q: number) {
  const options = props.question.options || []
  const answer = answerForClientQuestion(q)
  return answer.value?.choices
    .map((c, idx) => {
      const option = options.find((o) => o.code === '' + c)
      if (!option) return answer.value!.texts[idx] || ''
      if (option.allow_text) return answer.value!.texts[idx] || ''
      return option.text_for_consultant || option.text || answer.value!.texts[idx] || ''
    })
    .join(', ')
}

const remote = computed(() => {
  return answerForClientQuestion(props.question.id!)
})
</script>

<template>
  <section>
    <header>
      <div class="question-answer">
        <h4 :class="show ? 'show' : 'hidden'">
          {{ question.label ? question.label + ': ' : question.question_text }}
        </h4>
        <span v-if="show">
          {{ getAnswer(question.id!) }}
        </span>
      </div>

      <div class="buttons">
        <Button
          :icon="edit ? 'pi pi-times' : 'pi pi-pencil'"
          size="small"
          severity="secondary"
          @click="edit = !edit"
          v-if="allowEdit"
        />
      </div>
    </header>
    <section class="edit-answer" v-if="edit">
      <Panel header="Edit">
        <ClientQuestion
          :question="question"
          :remote="remote"
          ref="questionComponentRef"
          :hide-title="true"
        />
        <Button label="Submit Answer" @click.prevent="onSubmit()" />
      </Panel>
    </section>
  </section>
</template>

<style scoped>
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.buttons {
  display: flex;
  gap: 0.5rem;
}

.answer {
  margin: 0.5rem 0;
}

.current-answers {
  margin-left: 0.5rem;
}

h4,
h3 {
  margin: 0;
}

.question-answer {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  flex-wrap: wrap;
}
</style>
