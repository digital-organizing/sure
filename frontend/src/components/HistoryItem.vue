<script setup lang="ts">
import type {
  FlatClientAnswerSchema,
  FlatConsultantAnswerSchema,
  FlatTestResultSchema,
  FlatTestSchema,
  LogEntrySchema,
} from '@/client'
import { useUsers } from '@/composables/useUsers'
import { computed, onMounted, ref } from 'vue'

const props = defineProps<{
  type: 'client' | 'consultant' | 'test' | 'result' | 'log'
  item:
    | FlatClientAnswerSchema
    | FlatConsultantAnswerSchema
    | FlatTestSchema
    | FlatTestResultSchema
    | LogEntrySchema
  date: Date
  user?: number | null
}>()

const { getUser } = useUsers()

const fullName = ref<string>('')

onMounted(() => {
  if (props.user) {
    getUser(props.user)
      .then((user) => {
        fullName.value = `${user.first_name} ${user.last_name}`
      })
      .catch(() => {
        fullName.value = 'id: ' + props.user
      })
  }
})

function formatDate(date: Date): string {
  return date.toLocaleString()
}

const label = computed(() => {
  switch (props.type) {
    case 'client':
    case 'consultant':
      return 'Q: ' + props.item.label
    case 'test':
      return 'T: ' + props.item.label
    case 'result':
      return 'R: ' + props.item.label
    case 'log':
      return 'L: ' + props.item.label
    default:
      return 'Unknown Item'
  }
})

const value = computed(() => {
  switch (props.type) {
    case 'client':
      return (props.item as FlatClientAnswerSchema)!.texts!.join(', ')
    case 'consultant':
      return (props.item as FlatConsultantAnswerSchema)!.texts!.join(', ')
    case 'test':
      return ''
    case 'result':
      return (props.item as FlatTestResultSchema).test.label
    case 'log':
      return ''
  }
  return ''
})
</script>

<template>
  <div class="history-entry">
    <span class="label">{{ label }}</span>
    <span class="value">{{ value }}</span>
    <div class="meta">
      <span class="date">{{ formatDate(props.date) }}</span>
      <span class="user" v-if="fullName">{{ fullName }}</span>
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
  display: flex;
  flex-direction: column;
}

i {
  font-size: 0.5rem;
}

span {
  overflow: hidden;
}
</style>
