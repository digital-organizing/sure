<script setup lang="ts">
import { useCase } from '@/composables/useCase'
import { useUsers } from '@/composables/useUsers'
import { computed, onMounted, ref } from 'vue'

const { clientQuestionnaire, consultantQuestionnaire } = useCase()

const props = defineProps<{
  entry: {
    question: number
    type: 'client' | 'consultant'
    choices: Array<number>
    texts: Array<string>
  }
  date: Date
  user?: number | null
}>()

const { getUser } = useUsers()

const fullName = ref<string>('')

onMounted(() => {
  if (props.user) {
    getUser(props.user).then((user) => {
      fullName.value = `${user.first_name} ${user.last_name}`
    })
  }
})

function formatDate(date: Date): string {
  return date.toLocaleString()
}

function clientQuestionForId(id: number) {
  return clientQuestionnaire?.value?.sections
    .flatMap((s) => s.client_questions)
    .find((q) => q.id === id)
}

function consultantQuestionForId(id: number) {
  return consultantQuestionnaire?.value?.consultant_questions.find((q) => q.id === id)
}
const questionName = computed(() => {
  let question
  if (props.entry.type === 'client') {
    question = clientQuestionForId(props.entry.question)
  } else {
    question = consultantQuestionForId(props.entry.question)
  }
  return question ? question.question_text : 'Unknown Question'
})
</script>

<template>
  <div class="history-entry">
    <span class="label">{{ questionName }}</span>
    <span><i class="pi pi-pencil"></i> {{ props.entry.texts.join(', ') }}</span>
    <div class="meta">
      {{ formatDate(props.date) }} <span class="user" v-if="fullName"> - {{ fullName }}</span>
    </div>
  </div>
</template>

<style scoped>
.history-entry {
  display: flex;
  flex-direction: column;
}

.history-entry .label {
  font-weight: bold;
}

.history-entry .meta {
  font-size: 0.8rem;
  color: #666;
}

i {
  font-size: 0.5rem;
}
</style>
