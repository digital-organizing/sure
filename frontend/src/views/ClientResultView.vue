<script setup lang="ts">
import ClientResult from '@/components/ClientResult.vue';
import { useResults } from '@/composables/useResults';
import { onMounted, ref } from 'vue';

const key = ref('');
const caseId = ref('SUF-');

const {
    caseFetched,
    tests,
    notes,
    documents,
    infos,
    fetchCase,
    error,
} = useResults();

onMounted(() => {
    const storedCaseId = sessionStorage.getItem('client_case_id');
    const storedCaseKey = sessionStorage.getItem('client_case_key');
    if(storedCaseId && storedCaseKey) {
        caseId.value = storedCaseId;
        key.value = storedCaseKey;
        fetchCase(storedCaseId, storedCaseKey);
    }
});


async function onFetchCase() {
    sessionStorage.setItem('client_case_id', caseId.value);
    sessionStorage.setItem('client_case_key', key.value);

    await fetchCase(caseId.value, key.value);
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
            <Button label="Show Results" @click="onFetchCase"></Button>
            <Message v-if="error" :severity="'error'" :text="error"></Message>
        </section>
        <section v-else>
            <ClientResult :caseId="caseId" :caseKey="key" />
        </section>
        <Button label="Back" severity="secondary" @click="caseFetched = false" v-if="caseFetched"></Button>
    </section>
</template>