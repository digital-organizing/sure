<script setup lang="ts">
import type { SectionSchema } from '@/client';
import ClientBottomNavButtons from './ClientBottomNavButtons.vue';

import { userAnswersStore } from '@/stores/answers'
import { defineProps, defineEmits } from 'vue'
import ClientRecapSection from './ClientRecapSection.vue';


const props = defineProps<{
   hasNext: boolean
   hasPrevious: boolean
   section: SectionSchema
}>()

const emits = defineEmits<{
  (e: 'next'): void
  (e: 'previous'): void
  (e: 'submit'): void
}>()

// const answersStore = userAnswersStore()

</script>

<template>
    <div class="client-section-element">
        <div>
            <ClientRecapSection
            :section="props.section"/>
        </div>
        <div class="client-bottom-button-section">
            <ClientBottomNavButtons
            @next="emits('next')"
            @previous="emits('previous')"
            @submit="emits('submit')"
            :section="props.section"
            :has-next="props.hasNext"
            :has-previous="props.hasPrevious"
            />
        </div>
        
    </div>
</template>