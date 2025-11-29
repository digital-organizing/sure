<script setup lang="ts">
import { sureApiGetClientResults, sureApiGetDocumentLink, sureApiListCaseNotes, sureApiListDocuments, type TestSchema, type DocumentSchema, type NoteSchema, ResultInformationSchema, sureApiGetResultInfo } from '@/client';
import { ref } from 'vue';

const error = ref('');
const key = ref('');
const caseId = ref('SUF-');

const caseFetched = ref(false);

const notes = ref<NoteSchema[]>([]);
const documents = ref<DocumentSchema[]>([]);
const tests = ref<TestSchema[]>([]);
const infos = ref<ResultInformationSchema[]>([]);

async function downloadDocument(id) {
    const link = await sureApiGetDocumentLink({path: {doc_pk: id, pk: caseId.value}, body: {key: key.value}})
    if(link.data) {
        window.open(link.data.link, '_blank');
    }    
}

async function fetchCase() {
    await sureApiGetClientResults({ path: { pk: caseId.value }, body: { key: key.value } }).then((response) => {
        if (response.data) {
            tests.value = response.data;
            caseFetched.value = true;
        }
    }).catch((err) => {
        error.value = err.response?.data?.detail || 'An error occurred while fetching the case results.';
    });
    if(!caseFetched.value) {
        return;
    }
    sureApiListCaseNotes({path: {pk: caseId.value}, body: {key: key.value}}).then((response) => {
        if(response.data) {
            notes.value = response.data;
        }
    });
    sureApiListDocuments({path: {pk: caseId.value}, body: {key: key.value}}).then((response) => {
        if(response.data) {
            documents.value = response.data;
        }
    });
    sureApiGetResultInfo({path: {pk: caseId.value}, body: {key: key.value}}).then((response) => {
        if(response.data) {
            infos.value = response.data;
        }
    });
}

function getResult(test: TestSchema, optionId: number) {
    return test.test_kind.result_options.find((option) => option.id == optionId);
}

function infoForOption(optionId: number) {
    return infos.value.find((info) => info.option === optionId);
}

</script>

<template>
    <section>
        <section v-if="!caseFetched">
            <h2>Client Result View</h2>
            <InputGroup>
                <InputGroupAddon>SUF-</InputGroupAddon>
                <InputMask v-model="caseId" mask="*******"></InputMask>
            </InputGroup>
            <Password v-model="key" placeholder="Enter access key" :feedback="false"></Password>
            <Button label="Show Results" @click="fetchCase"></Button>
            <Message v-if="error" :severity="'error'" :text="error"></Message>
        </section>
        <section v-else>
            <h3>Case Results</h3>
            <!-- Display case results here -->
            <section class="results">
                <div v-for="test in tests" :key="test.id!" class="test-result">
                    {{ test.test_kind.name }}:
                    {{ getResult(test, test.results[0].result_option)?.label || 'No result' }}
                    <template v-if="infoForOption(test.results[0].result_option)">
                        {{ infoForOption(test.results[0].result_option)!.information_text }}
                    </template>
                </div>
            </section>
            <section class="notes">
                <h3>Case Notes</h3>
                <div v-for="note in notes" :key="note.id!" class="note">
                    <p>{{ note.note }}</p>
                </div>
            </section>
            <section class="documents">
                <h3>Documents</h3>
                <div v-for="document in documents" :key="document.id!" class="document">
                    <p>{{ document.name }}</p>
                    <Button label="Download" @click="downloadDocument(document.id!)"></Button>
                </div>
            </section>
        </section>
    </section>
</template>