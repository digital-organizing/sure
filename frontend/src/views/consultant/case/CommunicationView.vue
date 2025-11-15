<script lang="ts" setup>
import { useCase } from '@/composables/useCase'

const { visit } = useCase()
</script>

<template>
  {{ visit }}
</template>
