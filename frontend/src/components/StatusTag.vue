<script lang="ts" setup>
import { useStatus } from '@/composables/useStatus'

const props = defineProps<{
  value: string
}>()

const { labelForStatus } = useStatus()
</script>

<template>
  <Tag :value="labelForStatus(props.value)" rounded :class="props.value" class="status" />
</template>
