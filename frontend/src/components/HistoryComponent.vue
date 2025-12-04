<script lang="ts" setup>
import HistoryItem from './HistoryItem.vue'
import { useCase } from '@/composables/useCase'
import { useTexts } from '@/composables/useTexts'

defineProps<{ caseId: string }>()

const { historyItems } = useCase()
const { getText: t } = useTexts()
</script>

<template>
  <section>
    <HistoryItem
      v-for="item of historyItems.slice(0, 5)"
      :key="item.id!"
      :item="item.entry"
      :type="item.type"
      :date="new Date(item.entry.created_at)"
      :user="item.entry.user"
    />
    <Button
      class="mt-2"
      :label="t('view-full-history').value"
      asChild
      outlined
      v-slot="slotProps"
      severity="secondary"
      size="small"
    >
      <RouterLink
        :class="slotProps.class"
        :to="{ name: 'consultant-case-history', params: { caseId: caseId } }"
        >{{ t('view-full-history') }}</RouterLink
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
