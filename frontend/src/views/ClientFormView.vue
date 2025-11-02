<script setup lang="ts">
import { sureApiGetQuestionnaire, type QuestionnaireSchema } from '@/client';
import ClientSection from '@/components/ClientSection.vue';
import ProgressBar from '@/components/ProgressBar.vue';
import { onMounted, ref } from 'vue';


const formStructure = ref <QuestionnaireSchema|null>(null)
const formIndex = ref<number>(0)


onMounted(async ()=> {formStructure.value = (await sureApiGetQuestionnaire({path:{pk:2}})).data!})

function nextQuestion() {
    if (formIndex.value < (formStructure.value?.sections.length ?? 0) - 1) {
        formIndex.value++;
    }
}

function previousQuestion() {
    if (formIndex.value > 0) {
        formIndex.value--;
    }
}

</script>

<template>
    <div id="client-form-view">
    <div id="nav-bar">
        Navbar
    </div>
  <div v-if="formStructure">
    <h1>Client Form</h1>
    <ProgressBar :total="formStructure?.sections.length" :value="formIndex + 1" />
    <ClientSection @next="nextQuestion" @previous="previousQuestion" :section="formStructure?.sections[formIndex]!" :has-next="formIndex < (formStructure?.sections.length ?? 0) - 1" :has-previous="formIndex > 0" />
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
#client-form-view {
    max-width: 800px;
    margin: auto;
}
</style>
