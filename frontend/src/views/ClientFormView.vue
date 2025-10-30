<script setup lang="ts">
import { sureApiGetQuestionnaire, type QuestionnaireSchema } from '@/client';
import ClientSection from '@/components/ClientSection.vue';
import { onMounted, ref } from 'vue';
import Button from 'primevue/button';


const formStructure = ref <QuestionnaireSchema|null>(null)
const formIndex = ref<number>(0)


onMounted(async ()=> {formStructure.value = (await sureApiGetQuestionnaire({path:{pk:2}})).data!})


</script>

<template>
  <div v-if="formStructure">
    <h1>Client Form</h1>
    <ProgressBar :total="formStructure?.sections.length" :value="formIndex + 1" />
    <ClientSection :section="formStructure?.sections[formIndex]!" />
    <div>
        <Button label="Previous" icon="IconRightArrow" icon-pos="right" @click="formIndex--" rounded/>
        <Button @click="formIndex++" rounded >Next</Button>
    </div>
  </div>
</template>

<style scoped>
    div {
        margin: 20px;
    }
    button {
        margin: 10px;
    }
</style>
