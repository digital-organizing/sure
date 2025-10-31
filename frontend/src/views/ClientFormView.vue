<script setup lang="ts">
import { sureApiGetQuestionnaire, type QuestionnaireSchema } from '@/client';
import ClientSection from '@/components/ClientSection.vue';
import ProgressBar from '@/components/ProgressBar.vue';
import IconRightArrow from '@/components/icons/IconRightArrow.vue';
import IconLeftArrowSmall from '@/components/icons/IconLeftArrowSmall.vue';
import { onMounted, ref } from 'vue';
import Button from 'primevue/button';


const formStructure = ref <QuestionnaireSchema|null>(null)
const formIndex = ref<number>(0)


onMounted(async ()=> {formStructure.value = (await sureApiGetQuestionnaire({path:{pk:2}})).data!})


</script>

<template>
    <div id="nav-bar">
        Navbar
    </div>
  <div v-if="formStructure">
    <h1>Client Form</h1>
    <ProgressBar :total="formStructure?.sections.length" :value="formIndex + 1" />
    <ClientSection :section="formStructure?.sections[formIndex]!" />
    <div id="navi-bottom">
        <Button @click="formIndex--" size="small" severity="secondary" rounded>Previous <IconLeftArrowSmall /></Button>
        <Button @click="formIndex++" severity="primary" rounded >Next <IconRightArrow /></Button>
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
    #navi-bottom {
        display: flex;
        justify-content: space-between;
        margin-top: 30px;
    }
</style>
