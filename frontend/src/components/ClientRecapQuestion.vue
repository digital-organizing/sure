<script setup lang="ts">
import { defineProps } from 'vue'
import { type ClientQuestionSchema } from '@/client'

const props = defineProps<{
    question: ClientQuestionSchema
    index: number
}>()

</script>

<template>
    <p>One Question</p>
</template>