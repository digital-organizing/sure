<script setup lang="ts">
import { defineProps } from 'vue';
import { type ClientQuestionSchema } from '@/client';

const props = defineProps<{
  question: ClientQuestionSchema;
}>();

</script>

<template>
  <div class="client-question">
    <p>{{ props.question.question_text }}</p>
  </div>
</template>
