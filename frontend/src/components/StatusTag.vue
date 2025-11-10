<script lang="ts" setup>
import { useStatus } from '@/composables/useStatus'

const props = defineProps<{
  value: string
}>()

const { labelForStatus } = useStatus()

function getSeverity(value: string): string {
  switch (value.toLowerCase()) {
    case 'created':
      return 'success'
    case 'client_submitted':
      return 'info'
    case 'consultant_submitted':
      return 'warning'
    case 'results_recorded':
      return 'danger'
    case 'results_sent':
      return 'help'
    case 'closed':
      return 'dark'
    case 'canceled':
      return 'secondary'
    default:
      return 'secondary'
  }
}
</script>

<template>
  <Tag :value="labelForStatus(props.value)" rounded :severity="getSeverity(props.value)" />
</template>
