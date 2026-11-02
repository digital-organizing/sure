<script setup lang="ts">
import { sureApiCreateCaseView } from '@/client'
import { useLocations } from '@/composables/useLocations'
import { useQuestionnaires } from '@/composables/useQuestionnaires'
import { useTexts } from '@/composables/useTexts'
import { useClipboard } from '@vueuse/core'
import { useToast } from 'primevue/usetoast'

import { useQRCode } from '@vueuse/integrations/useQRCode'

import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const { locations, fetchLocations } = useLocations()
const { questionnaires, fetchQuestionnaires } = useQuestionnaires()
const { getText: t, language: currentLanguage, availableLanguages } = useTexts()

const questionnaire = ref<number | null>(null)
const location = ref<number | null>(null)
const externalId = ref<string>('')
const phone = ref<string>('')
// New cases default to the consultant's own interface language.
const language = ref<string>(currentLanguage.value ?? 'en')
watch(currentLanguage, (lang) => {
  if (lang) language.value = lang
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

// Questionnaire and location stay as chosen, the next case is usually created
// at the same place. Everything client specific is cleared.
function startNewCase() {
  link.value = ''
  caseId.value = ''
  externalId.value = ''
  phone.value = ''
  language.value = currentLanguage.value ?? 'en'

  // A new key re-mounts the form, which plays the enter transition, so it is
  // obvious that this is a fresh form and not the case just created.
  formKey.value++
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function focusFirstField() {
  document.getElementById('external_id')?.focus({ preventScroll: true })
}

const formKey = ref(0)

const router = useRouter()

function goToDashboard() {
  link.value = ''
  router.push({ name: 'consultant-dashboard' })
}

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
  <Transition name="new-case" mode="out-in" @after-enter="focusFirstField">
    <Form :key="formKey" @submit="handleSubmit" class="form-col stretch">
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
        <InputText
          id="phone"
          :label="t('mobile-phone-number').value"
          name="phone"
          v-model="phone"
        />
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
  </Transition>
  <Dialog
    v-if="link"
    :header="t('case-created-successfully').value"
    visible
    modal
    :closable="false"
    @hide="startNewCase"
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
        <Button :label="t('close-new-case', 'Close + New Case').value" @click="startNewCase" />
        <Button
          :label="t('go-to-dashboard', 'Go to Dashboard').value"
          severity="contrast"
          @click="goToDashboard"
        />
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
.new-case-leave-active {
  transition:
    opacity 0.2s ease-in,
    transform 0.2s ease-in;
}
.new-case-enter-active {
  transition:
    opacity 0.35s ease-out,
    transform 0.35s ease-out;
}
.new-case-leave-to {
  opacity: 0;
  transform: translateX(-2rem);
}
.new-case-enter-from {
  opacity: 0;
  transform: translateX(2rem);
}
@media (prefers-reduced-motion: reduce) {
  .new-case-enter-active,
  .new-case-leave-active {
    transition: opacity 0.2s;
  }
  .new-case-enter-from,
  .new-case-leave-to {
    transform: none;
  }
}
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
