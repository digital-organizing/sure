<script setup lang="ts">
const props = defineProps({
  total: Number,
  value: Number,
})
</script>

<template>
  <p id="progressbar">Progress: {{ props.value?.valueOf() }} / {{ props.total?.valueOf() }}</p>
</template>

<style scoped>
#progressbar {
    font-family: "Circular Std";
    font-size: 16px;
    margin: 0;
}
</style>
