<script lang="ts" setup>
import { sureApiGetDocumentLink, sureApiSetCaseKey, type DocumentSchema, type NoteSchema, type ResultInformationSchema, type TestSchema } from '@/client';
import TestResultItem from './TestResultItem.vue';
import { useResults } from '@/composables/useResults';
import { computed, onActivated, onMounted } from 'vue';
import LocationComponent from './LocationComponent.vue';


const props = defineProps<{
caseId: string,
caseKey: string

   }>();
const {
    caseFetched,
    tests,
    notes,
    documents,
    infos,
    fetchCase,
    caseStatus,
    location,
    error,
} = useResults();


async function downloadDocument(id) {
    const link = await sureApiGetDocumentLink({path: {doc_pk: id, pk: props.caseId}, body: {key: props.caseKey}})
    if(link.data) {
        window.open(link.data.link, '_blank');
    }    
}
function getResult(test: TestSchema, optionId: number) {
    return test.test_kind.result_options.find((option) => option.id == optionId);
}

function infoForOption(optionId: number) {
    return infos.value.find((info) => info.option === optionId);
}

const testsWithResults = computed(() => tests.value.filter(test => test.results.length > 0));
const displayResults = computed(() => caseStatus.value && caseStatus.value.value != 'not_available');

</script>

<template>
    <section class="client-result">
           <h3>Your Results (SUF-{{ props.caseId }})</h3>
            <!-- Display case results here -->
            <section v-if="!displayResults">
                Your results are available, please call your testing location during opening hours to obtain them.
                <LocationComponent :location="location" v-if="location" />
            </section>
            <section class="results" v-if="testsWithResults.length > 0 && displayResults">
                <div v-for="test in testsWithResults" :key="test.id!" class="test-result">
                    <TestResultItem :result="test.results[0]" :resultOption="getResult(test, test.results[0].result_option)!" :test="test" :infoText="infoForOption(test.results[0].result_option)?.information_text" />
                </div>
            </section>
            <Panel v-if="notes.length > 0 && displayResults" class="notes" header="Notes">
            <div v-for="note in notes" :key="note.id!" class="note">
                <p>{{ note.note }}</p>
            </div>
            </Panel>
            <Panel class="documents" header="Documents" v-if="documents.length > 0 && displayResults" toggleable>
                <div v-for="document in documents" :key="document.id!" class="document">
                    <p class="link" @click="downloadDocument(document.id!)">{{ document.name }}</p>
                    <Button icon="pi pi-download" size="small" variant="outlined" @click="downloadDocument(document.id!)"/>
                </div>
            </Panel>
</section>
</template>


<style scoped>
.client-result {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    align-items: stretch;
    margin-left: 5px;
    margin-right: 5px;
}
h3 {
    text-align: center;
    display: inline;
    margin-bottom: 0;

}
.document {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 0.5rem;
}
.note {
    margin-bottom: 0.5rem;
}
.link {
    text-decoration: underline;
    font-weight: bold;
    color: var(--text-color);
    cursor: pointer;
}
</style>