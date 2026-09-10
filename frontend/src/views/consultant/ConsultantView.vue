<script setup lang="ts">
import { useBanner } from '@/composables/useBanner'
import { useCase } from '@/composables/useCase'
import { useRender } from '@/composables/useRender'
import { useStatus } from '@/composables/useStatus'
import { useTexts } from '@/composables/useTexts'
import { formatDate } from '@vueuse/core'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const { showBanners, dismissBanner } = useBanner()
const { renderMarkdown } = useRender()
const { visit } = useCase()
const { formatText } = useTexts()
const { labelForStatus } = useStatus()
const route = useRoute()

// The visit is global state and outlives the case view, so only warn while
// the loaded visit is the case that is being displayed.
const currentVisit = computed(() =>
  visit.value && visit.value.case === route.params.caseId ? visit.value : null,
)

// Cases of other tenants always get the warning, own cases once they are
// older than a month.
const showPastCaseWarning = computed(() => {
  if (!currentVisit.value) return false
  if (currentVisit.value.other_tenant) return true
  const oneMonthAgo = new Date()
  oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1)
  return new Date(currentVisit.value.created_at) < oneMonthAgo
})

// Only closed cases are called closed, all others name their current status.
const pastCaseWarning = computed(() => {
  const status = currentVisit.value?.status ?? ''
  return formatText(status === 'closed' ? 'past-case-warning' : 'past-case-warning-open', [
    {
      key: 'date',
      value: formatDate(new Date(currentVisit.value?.created_at ?? ''), 'DD.MM.YYYY'),
    },
    { key: 'location', value: currentVisit.value?.location ?? '' },
    { key: 'status', value: labelForStatus(status) },
  ]).value
})
</script>

<template>
  <main>
    <header>
      <Message
        :severity="banner.severity"
        variant="outlined"
        closable
        v-for="banner in showBanners"
        :key="banner.id!"
        @close="dismissBanner(banner.id!)"
      >
        <div v-html="renderMarkdown(banner.content)" />
      </Message>
      <Message
        v-if="showPastCaseWarning"
        severity="warn"
        variant="outlined"
        icon="pi pi-exclamation-triangle"
      >
        {{ pastCaseWarning }}
      </Message>
    </header>
    <router-view />
  </main>
</template>

<style scoped>
main {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  gap: 1rem;
}
header {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
</style>
