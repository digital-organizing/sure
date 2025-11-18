<script lang="ts" setup>
import { useCase } from '@/composables/useCase'

defineProps<{ caseId: string }>()

const { visit } = useCase()
</script>

<template>
  {{ visit }}
</template>
