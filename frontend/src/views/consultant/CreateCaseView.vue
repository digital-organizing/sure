<script setup lang="ts">
import { sureApiCreateCaseView } from '@/client'
import { useLocations } from '@/composables/useLocations'
import { useQuestionnaires } from '@/composables/useQuestionnaires'
import { useClipboard } from '@vueuse/core'
import { useToast } from 'primevue/usetoast'
const toast = useToast()

import { useQRCode } from '@vueuse/integrations/useQRCode'

import { onMounted, ref } from 'vue'

const { locations, fetchLocations } = useLocations()
const { questionnaires, fetchQuestionnaires } = useQuestionnaires()

const questionnaire = ref<number | null>(null)
const location = ref<number | null>(null)
const externalId = ref<string>('')
const phone = ref<string>('')

const link = ref<string>('')
const caseId = ref<string>('')
const { copy, isSupported } = useClipboard()

const qrCode = useQRCode(link, {
  width: 200,
})

async function handleSubmit() {
  // Handle form submission logic here
  const response = await sureApiCreateCaseView({
    body: {
      questionnaire_id: questionnaire.value!,
      location_id: location.value!,
      external_id: externalId.value,
      phone: phone.value,
    },
  })

  if (response.data) {
    link.value = response.data.link
    caseId.value = response.data.case_id
  } else {
    alert('Error creating case. Please try again.')
  }
}

onMounted(() => {
  fetchLocations().then(() => {
    if (locations.value.length > 0) {
      location.value = locations.value[0].id!
    }
  })
  fetchQuestionnaires().then(() => {
    if (questionnaires.value.length > 0) {
      questionnaire.value = questionnaires.value[0].id!
    }
  })
})

function onCopy() {
  copy(link.value).then(() => {
    toast.add({
      severity: 'success',
      summary: 'Link Copied',
      detail: 'The case link has been copied to clipboard.',
      life: 3000,
    })
  })
}
</script>

<template>
  <Form @submit="handleSubmit" class="form-col stretch">
    <h2>Create New Case</h2>
    <div class="form-field">
      <label for="external_id">External ID</label>
      <InputText label="External ID" name="external_id" v-model="externalId" id="external_id" />
    </div>
    <div class="form-field">
      <label for="questionnaire_id">Questionnaire</label>
      <Select
        id="questionnaire_id"
        label="Questionnaire"
        name="questionnaire_id"
        :options="questionnaires"
        option-label="name"
        option-value="id"
        v-model="questionnaire"
      />
    </div>
    <div class="form-field">
      <label for="location_id">Location</label>
      <Select
        id="location_id"
        label="Location"
        name="location_id"
        :options="locations"
        option-label="name"
        option-value="id"
        v-model="location"
      />
    </div>
    <div class="form-field">
      <label for="phone">Phone</label>
      <InputText id="phone" label="Phone" name="phone" v-model="phone" />
    </div>
    <Button label="Create Case" type="submit" />
  </Form>
  <Dialog
    v-if="link"
    header="Case Created successfully"
    visible
    modal
    :closable="false"
    @hide="link = ''"
  >
    <div>
      <div class="qr-code">
        <img :src="qrCode" alt="QR Code" />
      </div>
      <p>Case has been created successfully. Share the following link with your client:</p>
      <span>Case ID: {{ caseId }}</span>

      <div class="case-link">
        <a :href="link" target="_blank">{{ link }}</a>
        <Button
          icon="pi pi-copy"
          severity="info"
          variant="link"
          @click="onCopy()"
          v-if="isSupported"
        />
      </div>

      <div class="dialog-buttons">
        <Button label="Close" @click="link = ''" />
        <Button label="Open client questionnaire" asChild v-slot="slotProps" severity="contrast">
          <a :href="link" target="_blank" :class="slotProps.class"> Open client questionnaire </a>
        </Button>
        <Button asChild v-slot="slotProps" severity="contrast">
          <RouterLink
            :to="{ name: 'consultant-case', params: { caseId: caseId } }"
            :class="slotProps.class"
          >
            Open consultant view
          </RouterLink>
        </Button>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.qr-code {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}
.case-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
</style>
