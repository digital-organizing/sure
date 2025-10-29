<script setup lang="ts">
import { type SectionSchema } from '@/client';
import ClientQuestion from './ClientQuestion.vue';


const props = defineProps<{section: SectionSchema}>();
</script>

<template>
  <div class="client-section">
    <p>{{ props.section.title }}</p>
    <ClientQuestion v-for="(question, idx) in props.section.client_questions" :key="question.id ?? idx" :question="question" />
  </div>
</template>