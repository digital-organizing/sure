<script lang="ts" setup>
import type { CaseHistory } from '@/client';
import { onMounted, ref, watch } from 'vue';
import HistoryItem from './HistoryItem.vue';
import { useCase } from '@/composables/useCase';


const props = defineProps<{ caseId: string}>()


const { historyItems } = useCase()


</script>

<template>
    <section>
    <HistoryItem v-for="item of historyItems" :key="item.id!" :entry="item" :date="new Date(item.created_at)" :user="item.user"/>
</section>
</template>