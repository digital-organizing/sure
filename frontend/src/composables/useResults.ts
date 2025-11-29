import { type LocationSchema, sureApiGetCaseStatus, sureApiGetClientResults, sureApiGetResultInfo, sureApiListCaseNotes, sureApiListDocuments, type DocumentSchema, type NoteSchema, type OptionSchema, type ResultInformationSchema, type TestSchema, tenantsApiGetLocationById } from "@/client";
import { createGlobalState } from "@vueuse/core";
import { ref } from "vue";


export const useResults = createGlobalState(() => {
    const notes = ref<NoteSchema[]>([]);
    const documents = ref<DocumentSchema[]>([]);
    const tests = ref<TestSchema[]>([]);
    const infos = ref<ResultInformationSchema[]>([]);
    const error = ref<string | null>(null);
    const caseFetched = ref(false);
    const location = ref<LocationSchema | null>(null);
    const caseStatus = ref<OptionSchema | null>(null);

    async function fetchCase(caseId: string, key: string, asClient = true) {
        await sureApiGetCaseStatus({path: { pk: caseId }, body: { key: key }}).then((response) => {
            if (response.data) {
                caseStatus.value = response.data;
            }
        });
        tenantsApiGetLocationById({path: { case_id: caseId }}).then((response) => {
            if (response.data) {
                location.value = response.data;
            }
        });

        await sureApiGetClientResults({ path: { pk: caseId }, body: { key: key }, query: {as_client: asClient} }).then((response) => {
            if (response.data) {
                tests.value = response.data;
                caseFetched.value = true;
            }
        }).catch((err) => {
            error.value = err.response?.data?.detail || 'An error occurred while fetching the case results.';
        });
        if (!caseFetched.value) {
            console.log("No case fetched, aborting further data fetch.");
            return;
        }
        sureApiListCaseNotes({ path: { pk: caseId }, body: { key: key } }).then((response) => {
            if (response.data) {
                notes.value = response.data;
            }
        });
        sureApiListDocuments({ path: { pk: caseId }, body: { key: key } }).then((response) => {
            if (response.data) {
                documents.value = response.data;
            }
        });
        sureApiGetResultInfo({ path: { pk: caseId }, body: { key: key } }).then((response) => {
            if (response.data) {
                infos.value = response.data;
            }
        });
    }

    return {
        notes,
        documents,
        tests,
        infos,
        fetchCase,
        error,
        caseFetched,
        location,
        caseStatus,
    };

})