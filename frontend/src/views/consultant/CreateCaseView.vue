<script setup lang="ts">
import { sureApiCreateCaseView } from '@/client'
import { useLocations } from '@/composables/useLocations'
import { useQuestionnaires } from '@/composables/useQuestionnaires'

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

const qrCode = useQRCode(link)

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
</script>

<template>
  <Form @submit="handleSubmit">
    <InputText label="External ID" name="external_id" v-model="externalId" />
    <Select
      label="Questionnaire"
      name="questionnaire_id"
      :options="questionnaires"
      option-label="name"
      option-value="id"
      v-model="questionnaire"
    />
    <Select
      label="Location"
      name="location_id"
      :options="locations"
      option-label="name"
      option-value="id"
      v-model="location"
    />
    <InputText label="Phone" name="phone" v-model="phone" />
    <Button label="Create Case" type="submit" />
  </Form>
  <img :src="qrCode" alt="QR Code" />
  <a :href="link" v-if="link">{{ link }}</a>
  <RouterLink :to="{ name: 'consultant-case', params: { caseId: caseId } }" v-if="caseId"
    >Consultant View</RouterLink
  >
</template>
