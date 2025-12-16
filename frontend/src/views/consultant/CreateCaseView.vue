<script setup lang="ts">
import { sureApiCreateCaseView } from '@/client'
import { useLocations } from '@/composables/useLocations'
import { useQuestionnaires } from '@/composables/useQuestionnaires'
import { useTexts } from '@/composables/useTexts'
import { useClipboard } from '@vueuse/core'
import { useToast } from 'primevue/usetoast'

import { useQRCode } from '@vueuse/integrations/useQRCode'

import { onMounted, ref } from 'vue'

const { locations, fetchLocations } = useLocations()
const { questionnaires, fetchQuestionnaires } = useQuestionnaires()
const {
  getText: t,
  language: currentLanguage,
  getLanguage,
  getAvailableLanguages,
  onLanguageChange,
  availableLanguages,
} = useTexts()

const questionnaire = ref<number | null>(null)
const location = ref<number | null>(null)
const externalId = ref<string>('')
const phone = ref<string>('')
const language = ref<string>('en')

onMounted(() => {
  getAvailableLanguages().then(() => {
    getLanguage().then((lang) => {
      language.value = lang!
    })
  })
  language.value = currentLanguage.value!
  onLanguageChange((newLang) => {
    language.value = newLang!
  })
})

const link = ref<string>('')
const caseId = ref<string>('')
const { copy, isSupported } = useClipboard()
const toast = useToast()

const qrCode = useQRCode(link, {
  width: 250,
})

async function handleSubmit() {
  // Handle form submission logic here
  const response = await sureApiCreateCaseView({
    body: {
      questionnaire_id: questionnaire.value!,
      location_id: location.value!,
      external_id: externalId.value,
      phone: phone.value,
      language: language.value,
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
      location.value = locations.value[0]!.id!
    }
  })
  fetchQuestionnaires().then(() => {
    if (questionnaires.value.length > 0) {
      questionnaire.value = questionnaires.value[0]!.id!
    }
  })
})

function onCopy() {
  copy(link.value).then(() => {
    toast.add({
      severity: 'success',
      summary: t('link-copied').value,
      detail: t('link-copied-detail').value,
      life: 3000,
    })
  })
}
</script>

<template>
  <Form @submit="handleSubmit" class="form-col stretch">
    <h2>{{ t('create-new-case') }}</h2>
    <div class="form-field">
      <label for="external_id">{{ t('internal-id') }}</label>
      <InputText
        :label="t('internal-id').value"
        name="external_id"
        v-model="externalId"
        id="external_id"
      />
      <Message size="small" severity="secondary" variant="simple">{{
        t('internal-id-help')
      }}</Message>
    </div>
    <div class="form-field">
      <label for="questionnaire_id">{{ t('questionnaire') }}</label>
      <Select
        id="questionnaire_id"
        :label="t('questionnaire').value"
        name="questionnaire_id"
        :options="questionnaires"
        option-label="name"
        option-value="id"
        v-model="questionnaire"
      />
    </div>
    <div class="form-field">
      <label for="location_id">{{ t('location') }}</label>
      <Select
        id="location_id"
        :label="t('location').value"
        name="location_id"
        :options="locations"
        option-label="name"
        option-value="id"
        v-model="location"
      />
    </div>
    <div class="form-field">
      <label for="phone">{{ t('mobile-phone-number') }}</label>
      <InputText id="phone" :label="t('mobile-phone-number').value" name="phone" v-model="phone" />
      <Message size="small" severity="secondary" variant="simple">{{
        t('phone-number-help')
      }}</Message>
    </div>
    <div class="form-field">
      <label for="language">{{ t('preferred-language') }}</label>
      <SelectButton v-model="language" :options="availableLanguages.map((lang) => lang[0])">
      </SelectButton>
      <Message size="small" severity="secondary" variant="simple">{{
        t('preferred-language-help')
      }}</Message>
    </div>
    <Button :label="t('create-case').value" type="submit" />
  </Form>
  <Dialog
    v-if="link"
    :header="t('case-created-successfully').value"
    visible
    modal
    :closable="false"
    @hide="link = ''"
  >
    <div>
      <div class="qr-code">
        <img :src="qrCode" alt="QR Code" />
      </div>
      <p>{{ t('case-created-message') }}</p>
      <span>{{ t('case-id') }}: {{ caseId }}</span>

      <div class="case-link">
        <a :href="link" target="_blank">{{ link }}</a>
        <Button
          icon="pi pi-copy"
          severity="contrast"
          variant="link"
          @click="onCopy()"
          v-if="isSupported"
        />
      </div>

      <div class="dialog-buttons">
        <Button :label="t('close').value" @click="link = ''" />
        <Button
          :label="t('open-client-questionnaire').value"
          asChild
          v-slot="slotProps"
          severity="contrast"
        >
          <a :href="link" target="_blank" :class="slotProps.class">
            {{ t('open-client-questionnaire') }}
          </a>
        </Button>
        <Button asChild v-slot="slotProps" severity="contrast">
          <RouterLink
            :to="{ name: 'consultant-case', params: { caseId: caseId } }"
            :class="slotProps.class"
          >
            {{ t('open-consultant-view') }}
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
