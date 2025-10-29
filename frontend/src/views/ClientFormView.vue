<script setup lang="ts">
import { sureApiGetQuestionnaire, type QuestionnaireSchema } from '@/client';
import ClientSection from '@/components/ClientSection.vue';
import { onMounted, ref } from 'vue';

const formStructure = ref <QuestionnaireSchema|null>(null)
const formIndex = ref<number>(0)


onMounted(async ()=> {formStructure.value = (await sureApiGetQuestionnaire({path:{pk:2}})).data!})


</script>

<template>
  <div v-if="formStructure">
    <h1>AA</h1>
    <ClientSection :section="formStructure?.sections[formIndex]!" />
    <button @click="formIndex--">Previous</button>
    <button @click="formIndex++">Next</button>
  </div>
</template>