<script setup lang="ts">

const props = defineProps(
    {
        total: Number,
        value: Number,
    }
)

</script>

<template>
    <p>Progress: {{ props.value?.valueOf() }} / {{ props.total?.valueOf() }}</p>
</template>