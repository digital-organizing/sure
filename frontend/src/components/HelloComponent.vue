<script setup lang="ts">
const props = defineProps<{ name: string }>()
</script>

<template>
  <h1>Hello from HelloComponent.vue!</h1>
  <p>{{ props.name }}</p>
</template>
