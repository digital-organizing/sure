<script lang="ts" setup>
import { useCase } from '@/composables/useCase'

defineProps<{ caseId: string }>()

const { historyItems, fetchCaseHistory } = useCase()

function loadMoreHistory() {
  fetchCaseHistory(20, true)
}
</script>

<template>
  <section>
    <header class="case">
      <h2>Case History</h2>
    </header>
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
