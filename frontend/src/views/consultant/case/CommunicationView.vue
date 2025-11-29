<script lang="ts" setup>
import { sureApiGetCaseStatus, sureApiGetNonSmsResults, sureApiGetPhoneNumber, type TestSchema } from '@/client';
import ClientResult from '@/components/ClientResult.vue';
import { useCase } from '@/composables/useCase';
import { useResults } from '@/composables/useResults';
import { computed, onActivated, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

const props = defineProps<{ caseId: string }>()

const { publishResults, setCaseStatus } = useCase();
const phoneNumber = ref('');
const nonSmsResults = ref<TestSchema[]>([]);

function getPhoneNumber() {
  sureApiGetPhoneNumber({path: {pk: props.caseId}}).then(response => {
    if (response.data) {
      phoneNumber.value = '' + response.data.message
    } else {
      phoneNumber.value = 'Phone number not available'
    }
  });
}

const router = useRouter();
const { fetchCase, caseStatus } = useResults();

onMounted(async () => {
  await fetchCase(props.caseId, '', false);
  if (caseStatus.value?.value == 'not_available') {
    sureApiGetNonSmsResults({path: {pk: props.caseId}}).then(response => {
      // Handle non-SMS results if needed
      nonSmsResults.value = response.data || [];
    });
  }
});

onActivated(async () => {
  await fetchCase(props.caseId, '', false);
  if (caseStatus.value?.value == 'not_available') {
    sureApiGetNonSmsResults({path: {pk: props.caseId}}).then(response => {
      // Handle non-SMS results if needed
      nonSmsResults.value = response.data || [];
    });
  }
});

const nonSmsTests = computed(() => {
  return nonSmsResults.value.filter(test => test.results.length > 0);
})

function onBack() {
  router.push({ name: 'consultant-results', params: { caseId: props.caseId } })
}

function onPublishResults() {
  publishResults();

}
function onCaseClosed() {
  setCaseStatus('closed').then(() => {
    fetchCase(props.caseId, '', false);
  });
}
</script>

<template>
  <header class="case">
    <h2>Communication</h2>
  </header>
  <section class="client-preview">
    <section>
    <p>This is how the client will see their results:</p>
    <Button label="Refresh Preview" severity="info" @click="fetchCase(props.caseId, '', false)" />
</section>
  <ClientResult :caseId="props.caseId" :caseKey="''" class="preview" />
  </section>  
  
  <section>
    <Message severity="warn"  v-if="caseStatus?.value == 'not_available'">
    Results cannot be communicated to the client per SMS, you need to call them to provide the results.
         </Message>
    <Button label="Show Phone Number" severity="info" @click="getPhoneNumber()" v-if="phoneNumber === ''" />
    <Button label="Publish Results" v-if="caseStatus?.value == 'results_recorded'" severity="primary" @click="onPublishResults"></Button>
    <Button label="Close case" v-if="caseStatus?.value != 'closed'" @click="onCaseClosed"></Button>
    <span v-if="phoneNumber">{{ phoneNumber }}</span>
    <div v-if="caseStatus?.value == 'not_available'">
      <h4>These results cannot be communicated via SMS:</h4>
      <div v-for="test in nonSmsTests" :key="test.id!" :style="{'--result-color': test.results[0] ? (test.test_kind.result_options.find(option => option.id === test.results[0].result_option)?.color || '#000') : '#000'}" class="non-sms-result">
        <span class="test-name">
        {{ test.test_kind.name }}
        </span>

        <span class="result">
        {{ test.test_kind.result_options.find(option => option.id === test.results[0].result_option)?.label }}
        </span>
      </div>
    </div>
  <CaseNoteComponent class="row" />
  </section>
  
  <section>

  </section>

  <section class="case-footer">
    <Button label="Back" severity="secondary" @click="onBack()" />
  </section>
</template>

<style scoped>
.preview {
  max-width: 420px;
  max-height: 520px;
  overflow-y: auto;
}
.non-sms-result {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.3rem;
}
.result {
  background-color: var(--result-color);
  color: white;
  padding: 0.2rem 0.5rem;
  border-radius: 5px;
  font-weight: bold;
}
</style>