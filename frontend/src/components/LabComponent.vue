<script lang="ts" setup>
import type { PatientDataSchema } from '@/client'
import { useCase } from '@/composables/useCase'
import { useLab } from '@/composables/useLab'
import { usePrinter } from '@/composables/usePrinter'
import { useTests } from '@/composables/useTests'
import { useTexts } from '@/composables/useTexts'
import { Tag } from 'primevue'
import { computed, ref, watch } from 'vue'

defineProps({
  dirty: {
    type: Boolean,
    required: false,
    default: false,
  },
})

const { getText: t } = useTexts()

const {
  generateBarcodePdf,
  hasConnectedPrinter,
  printers,
  availablePrinters,
  printLabels,
  refreshPrinters,
  initialize,
  isInitialized,
} = usePrinter()

const { labInfo, labOrders, submitLabOrder, cancelLabOrder } = useLab()
const {
  visit,
  selectedTests,
  clientAnswers,
  clientQuestionnaire,
  onCaseRefresh,
  fetchClientAnswers,
  fetchClientSchema,
} = useCase()

const { testKinds } = useTests()

function getValueFor(label: string) {
  const question = clientQuestionnaire.value?.sections
    .flatMap((s) => s.client_questions)
    .find((q) => q.code === label)

  if (!question) return null

  const answer = clientAnswers.value?.find((a) => a.question === question.id)

  if (!answer) return null
  const option = question.options?.find((opt) => +opt.code === answer.choices[0]!)
  if (!option) return answer.texts?.[0] || null

  return option.allow_text
    ? answer.texts?.[0] || null
    : option.text_for_consultant || option.text || null
}

const selectedPrinter = ref<string | null>(null)

if (!isInitialized.value) {
  initialize()
    .then(() => refreshPrinters())
    .then(() => {
      if (hasConnectedPrinter.value && availablePrinters.value.length > 0) {
        selectedPrinter.value = availablePrinters.value[0]!.name
      }
    })
    .catch((error) => {
      console.error('Error initializing printer:', error)
    })
}

const dialogVisible = ref(false)

watch(dialogVisible, (visible) => {
  if (visible) {
    prefillPatientData()
  }
})

const birthYear = ref<number | null>(null)

watch(birthYear, (newYear) => {
  if (newYear) {
    const year = newYear
    patientData.value.birth_year = year
  } else {
    patientData.value.birth_year = 0
  }
})

const patientData = ref<PatientDataSchema>({
  birth_year: 0,
  gender: '',
  note: '',
})

async function prefillPatientData() {
  await Promise.all([fetchClientAnswers(), fetchClientSchema()])

  const birthYearValue = getValueFor('SEDFACT-BIRTHYEAR')

  if (birthYearValue) {
    const yearNum = parseInt(birthYearValue, 10)
    if (!isNaN(yearNum)) {
      birthYear.value = yearNum
    } else {
      birthYear.value = 2000
    }
  }

  patientData.value.gender = getValueFor('SEDFACT-GENDER') || ''
}

onCaseRefresh(() => {
  prefillPatientData()
})

prefillPatientData()

function isPatientDataComplete(): boolean {
  return patientData.value.birth_year !== 0 && patientData.value.gender.trim() !== ''
}

const allCancelled = computed(() => {
  return (
    labOrders.value.every((order) => order.status === 'cancelled') || labOrders.value.length === 0
  )
})

const openOrder = computed(() => {
  return labOrders.value.find((order) => order.status !== 'cancelled')
})

const availableProfiles = computed(() => {
  if (!labInfo.value || !labInfo.value.profiles) {
    return []
  }
  return labInfo.value.profiles.filter((profile) => {
    return selectedTests.value.some((test) => test.test_kind.id! === profile.test_kind)
  })
})

function testName(pk: number): string {
  const testKind = testKinds.value.find((tk) => tk.id === pk)
  return testKind ? testKind.name : 'Unknown Test'
}

function submitOrder() {
  if (!isPatientDataComplete()) {
    return
  }

  submitLabOrder(visit.value!.case, patientData.value).then((x) => {
    if (!x) return

    printBarcodes(x.codes)
  })
}

async function printBarcodes(codes: string[]) {
console.log('Printing barcodes:', codes)
  if (hasConnectedPrinter.value) {
    await printLabels(codes)
    return
  }
  await generateBarcodePdf(codes, {
    filename: `${visit.value?.case}_lab_barcodes.pdf`,
    download: true, // false um nur Blob zu erhalten
    pageWidth: 89, // Standard DYMO Label-Breite (mm)
    pageHeight: 36, // Standard DYMO Label-Höhe (mm)
  })
}

function codeForProfile(profile: string): string[] {
  const order = openOrder.value
  if (!order) {
    return []
  }
  console.log('Finding code for profile', profile, 'in order', order)
  console.log('Order profiles:', labInfo.value?.profiles)
  const labProfile = labInfo.value?.profiles.find((p) => p.profile_code === profile)

  if (!labProfile) {
    return []
  }
  const requiredMaterialCodes = labProfile.material_codes
  console.log(requiredMaterialCodes)
  console.log(order.codes)
  console.log(order.materials)


  return requiredMaterialCodes?.map((code) => order.codes[order.materials.findIndex((c) => c === code)] || '') || []

}

function openDialog() {
  dialogVisible.value = true
}

defineExpose({
  openDialog,
})
</script>

<template>
  <Button
    :label="'Order Tests from' + (labInfo ? ' ' + labInfo.name : '')"
    v-if="labInfo && availableProfiles.length > 0"
    @click="dialogVisible = true"
    :disabled="dirty"
  ></Button>
  <Dialog
    v-model:visible="dialogVisible"
    modal
    :header="'Order Tests from' + (labInfo ? ' ' + labInfo.name : '')"
    style="width: 90%; max-width: 1400px"
    v-if="visit"
  >
    <section class="order-dialog">
      <section class="printer">
        <div class="print-select" v-if="hasConnectedPrinter && availablePrinters.length > 0">
          <div class="form-field">
            <label>{{ t('select-printer') }}: </label>
            <Select
              v-model="selectedPrinter"
              :label="t('select-printer')"
              :options="printers"
              option-label="name"
              option-value="name"
              :option-disabled="(p) => !p.isConnected"
            />
          </div>
        </div>
        <Message v-if="!hasConnectedPrinter" severity="secondary">{{
          t('no-printer-connected')
        }}</Message>
        <Button @click="refreshPrinters" severity="secondary">{{ t('refresh-printers') }}</Button>
      </section>

      <section class="form">
        <h3>{{ t('patient-information') }}</h3>
        <Message v-if="!allCancelled" severity="info">{{ t('existing-lab-orders') }}</Message>
        <p>
          {{ t('fill-patient-info') }}
        </p>
        <Form class="form-col" :class="{ disabled: !allCancelled }">
          <div class="form-field">
            <label>{{ t('birth-year') }}: </label>
            <InputNumber
              v-model="patientData.birth_year"
              :label="t('birth-year')"
              required
              :use-grouping="false"
            />
          </div>
          <div class="form-field">
            <label>{{ t('gender') }}: </label>
            <InputText v-model="patientData.gender" :label="t('gender')" required />
          </div>
          <div class="form-field">
            <label>{{ t('note') }} ({{ t('optional') }}): </label>
            <Textarea v-model="patientData.note" :label="t('note')" rows="5" />
          </div>

          <Button
            :label="t('submit-order').value"
            :disabled="!isPatientDataComplete()"
            @click="submitOrder"
          ></Button>
        </Form>
      </section>

      <section class="profiles">
        <h3>{{ t('test-ordered') }}</h3>
        <div v-for="profile in availableProfiles" :key="profile.profile_code" class="profile-card">
          <span class="name">
            {{ testName(profile.test_kind) }}
          </span>
          <span class="print" v-if="codeForProfile(profile.profile_code)">
            <Button
              size="small"
              icon="pi pi-print"
              severity="secondary"
              rounded
              @click="printBarcodes(codeForProfile(profile.profile_code))"
              :label="t('print').value + ' (' + codeForProfile(profile.profile_code).length + ')' "
            />
          </span>
          <span class="code">
            {{ profile.profile_code }}
          </span>
          <div class="materials">
          <div class="material" v-for="code, idx in profile.material_codes" :key="code">
            <strong>{{ t('material') }}:</strong> {{ profile.materials![idx] }} ({{
              code
            }})
          </div>
        </div>
          <span class="note">
            {{ profile.note }}
          </span>
          <span class="pricing">
            <strong>{{ t('price-vct') }}</strong> {{ profile.price_vct || '-' }} CHF
            <strong>{{ t('price-kk') }}</strong> {{ profile.price_kk || '-' }} CHF
          </span>
        </div>
      </section>

      <section class="orders" v-if="labOrders.length > 0">
        <h3>{{ t('orders') }}</h3>
        <div v-for="order in labOrders" :key="order.order_number" class="order-card">
          <div class="info">
            <div class="order-number">
              <strong>{{ t('order-number') }}:</strong> {{ order.order_number }}
            </div>
            <div class="status">
              <strong>{{ t('status') }}:</strong>
              <Tag :value="order.status" severity="contrast" class="created" />
            </div>
            <div>
              <strong>{{ t('created-at') }}:</strong>
              <span>{{ new Date(order.created_at).toLocaleString() }}</span>
            </div>
          </div>

          <div class="codes">
            <strong>{{ t('barcodes') }}:</strong>
            <ul>
              <li v-for="code, idx in order.codes" :key="'' + code">
                {{ code }}
                ({{ order.materials[idx] }})
                <Button v-if="order.status != 'cancelled'" size="small" icon="pi pi-print" severity="secondary" rounded @click="printBarcodes([code])" :label="t('print').value" />
              </li>
            </ul>
          </div>
          
          <div class="note">
           {{ order.note }}
          </div>

          <div class="actions">
            <Button
              severity="primary"
              size="small"
              v-if="order.status != 'cancelled' && order.codes && order.codes.length > 0"
              @click="printBarcodes(order.codes)"
              icon="pi pi-print"
              :label="t('print-barcodes').value"
            />
            <Button
              variant="outlined"
              size="small"
              v-if="order.status === 'generated'"
              @click="cancelLabOrder(visit.case, order.order_number)"
              >{{ t('cancel') }}</Button
            >
          </div>
        </div>
      </section>
    </section>
  </Dialog>
</template>

<style scoped>
.order-dialog {
  display: grid;
  gap: 2rem;
  grid-template-areas:
    'form profiles'
    'form orders'
    'printer printer';
  grid-template-columns: 1.5fr 2fr;
  grid-template-rows: auto auto 1fr;
  padding: 1rem 2rem;
}

.actions {
  display: flex;
  gap: 2rem;
}

.order-card {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 0.9rem;
  margin-bottom: 0.5rem;
  gap: 0.5rem 2rem;

  display: grid;
  grid-template-areas:
    'info codes'
    'note codes'
    'actions actions';
}

.order-card .note {
  grid-area: note;
  color: black;
}

.info {
  grid-area: info;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info > div {
  display: flex;
  gap: 0.5rem;
  justify-content: space-between;
}

.codes {
  grid-area: codes;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.actions {
  margin-top: 0.5rem;
  display: flex;
  gap: 0.5rem;
  grid-area: actions;
}

.form-col.disabled {
  pointer-events: none;
  opacity: 0.6;
}

.printer {
  grid-area: printer;
  display: flex;
  flex-direction: row;
  width: 100%;
  gap: 1rem;
  justify-content: flex-start;
  align-items: center;
}

.form {
  grid-area: form;
  display: flex;
  flex-direction: column;
}
.form-col {
  margin-top: 1rem;
}

.profile-card {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 0.5rem;
  margin-bottom: 0.5rem;
  gap: 0.5rem;
  display: grid;
  grid-template-areas:
    'name code'
    'note pricing'
    'material print';
  grid-template-columns: 1fr auto;
}

.note {
  grid-area: note;
  color: #555;
}

.pricing {
  grid-area: pricing;
  color: #555;
}

.profile-card .name {
  grid-area: name;
  font-weight: bold;
}

.profile-card .profile {
  grid-area: profile;
  text-align: right;
}

.profile-card .code {
  grid-area: code;
  justify-self: end;
}

.profile-card .materials {
  grid-area: material;
  color: #555;
  align-self: center;
}

.profiles {
  grid-area: profiles;
}
.orders {
  grid-area: orders;
}

ul {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.print {
  grid-area: print;
  justify-self: end;
}
</style>
