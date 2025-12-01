<script lang="ts" setup>
import HistoryItem from '@/components/HistoryItem.vue'
import { useCase } from '@/composables/useCase'
import { useTexts } from '@/composables/useTexts'

defineProps<{ caseId: string }>()

const { historyItems, fetchCaseHistory } = useCase()
const { getText: t } = useTexts()

function loadMoreHistory() {
  fetchCaseHistory(20, true)
}
</script>

<template>
  <section>
    <header class="case">
      <h2>{{ t('case-history-title').value }}</h2>
    </header>
    <HistoryItem
      v-for="item of historyItems"
      :key="item.id!"
      :item="item.entry"
      :type="item.type"
      :date="new Date(item.entry.created_at)"
      :user="item.entry.user"
    />

    <Button
      @click="loadMoreHistory"
      :label="t('load-more').value"
      class="mt-2"
      severity="secondary"
    />
  </section>
</template>
