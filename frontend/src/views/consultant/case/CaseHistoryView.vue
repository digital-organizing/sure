<script lang="ts" setup>
import { useCase } from '@/composables/useCase'

defineProps<{ caseId: string }>()

const { historyItems, fetchCaseHistory } = useCase()

function loadMoreHistory() {
  // Placeholder for loading more history items
  // Implement pagination or fetching more items as needed
  fetchCaseHistory(20, true)
}
</script>

<template>
  <section>
    <h2>Case History</h2>
    <HistoryItem
      v-for="item of historyItems"
      :key="item.id!"
      :entry="item"
      :date="new Date(item.created_at)"
      :user="item.user"
    />

    <Button @click="loadMoreHistory" label="Load More" class="mt-2" severity="secondary" />
  </section>
</template>
