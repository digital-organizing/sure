<script lang="ts" setup>
import { useTexts } from '@/composables/useTexts'

const { getText: t } = useTexts()
</script>

<template>
  <h3>{{ t('past-visits') }}</h3>
</template>
