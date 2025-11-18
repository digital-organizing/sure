<script lang="ts" setup>
import type { AnswerSchema, ClientQuestionSchema } from '@/client'
import { useCase } from '@/composables/useCase'
import ClientQuestion from './ClientQuestion.vue'
import { computed, ref } from 'vue'

const props = defineProps<{
  question: ClientQuestionSchema
}>()

const questionComponentRef = ref<{ getClientAnswer: () => AnswerSchema } | null>(null)

const edit = ref(false)

const show = ref(props.question.do_not_show_directly ? false : true)

const {
  answerForClientQuestion,
  mapAnswersForClientQuestion,
  submitClientAnswer,
  fetchVisitDetails,
} = useCase()

function onSubmit() {
  if (questionComponentRef.value) {
    const answer = questionComponentRef.value.getClientAnswer()
    submitClientAnswer(answer).then(() => {
      fetchVisitDetails()
    })
    edit.value = false
  }
}

const remote = computed(() => {
  return answerForClientQuestion(props.question.id!)
})
</script>

<template>
  <section>
    <header>
      <h3 :class="show ? 'show' : 'hidden'">{{ question.question_text }}</h3>
      <div class="buttons">
        <Button
          :icon="show ? 'pi pi-eye-slash' : 'pi pi-eye'"
          size="small"
          severity="secondary"
          @click="show = !show"
        />
        <Button icon="pi pi-pencil" size="small" severity="secondary" @click="edit = !edit" />
      </div>
    </header>
    <section v-if="show" class="current-answers">
      <div v-for="answers in mapAnswersForClientQuestion(question.id!)" :key="answers.id">
        <p class="answer">
          <strong>{{ answers.code }}</strong
          >: {{ answers.text }}
        </p>
      </div>
    </section>
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
h3 {
  margin: 0;
}
</style>
