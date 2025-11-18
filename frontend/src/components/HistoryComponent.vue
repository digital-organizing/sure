<script lang="ts" setup>
import HistoryItem from './HistoryItem.vue'
import { useCase } from '@/composables/useCase'

defineProps<{ caseId: string }>()

const { historyItems } = useCase()
</script>

<template>
  <section>
    <HistoryItem
      v-for="item of historyItems.slice(0, 5)"
      :key="item.id!"
      :entry="item"
      :date="new Date(item.created_at)"
      :user="item.user"
    />
    <Button
      class="mt-2"
      label="View Full History"
      asChild
      outlined
      v-slot="slotProps"
      severity="secondary"
      size="small"
    >
      <RouterLink
        :class="slotProps.class"
        :to="{ name: 'consultant-case-history', params: { caseId: caseId } }"
        >View Full History</RouterLink
      >
    </Button>
  </section>
</template>

<style scoped>
section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.9rem;
}
</style>
