<script setup lang="ts">
import { sureApiGetCaseQuestionnaire, type QuestionnaireSchema } from '@/client'
import ClientNavigationTop from '@/components/ClientNavigationTop.vue'
import IconPhone from '@/components/icons/IconPhone.vue'
import IconPen from '@/components/icons/IconPen.vue'
import IconRightArrow from '@/components/icons/IconRightArrow.vue'
import { userAnswersStore } from '@/stores/answers'
import { computed, onMounted, ref } from 'vue'
import { RadioButton, InputText } from 'primevue'

const props = defineProps<{
  caseId: string
}>()

const formStructure = ref<QuestionnaireSchema | null>(null)
const answersStore = userAnswersStore()
const selectedConsentOption = ref<'yes' | 'no' | null>(null)
const phoneNumber = ref('')
const dateOfBirth = ref('')
const showContactForm = computed(() => selectedConsentOption.value === 'yes')

onMounted(async () => {
  formStructure.value = (await sureApiGetCaseQuestionnaire({ path: { pk: props.caseId } })).data!
  answersStore.setSchema(formStructure.value)

  const savedId = localStorage.getItem('clientFormCaseId')
  if (savedId !== props.caseId) {
    localStorage.setItem('clientFormCaseId', props.caseId)
    localStorage.setItem('clientFormIndex', '0')
  }
})
</script>

<template>
  <div v-if="formStructure" class="client-form-view">
    <div class="client-section-element" id="navi-top">
      <ClientNavigationTop
        :section-title="'Privacy'"
        :sections="formStructure.sections"
        :language-selector-only="true"
      />
    </div>
    <div class="client-section-element" id="phone-flex">
      <div class="client-phone-body">
        <p>
          Text to follow from data protection specialist For the test results and future
          consultations, there are two ways we can identify you. In either case, your data is secure
          and access is strictly regulated:
        </p>
      </div>
      <div class="client-phone-icon">
        <IconPhone />
      </div>
      <div class="client-phone-subtitle">Mobile phone number & date of birth</div>
      <div class="client-phone-body">
        You will receive a text message to access your test results. In your next consultation, your
        consultant will be able to access your previous information. You will also receive a test
        reminder via text message when it is appropriate. More information about our data use.
      </div>
      <div class="client-phone-icon">
        <IconPen />
      </div>
      <div class="client-phone-subtitle">Identification number (ID)</div>
      <div class="client-phone-body">
        You will receive a random ID. To receive your test results, you must contact us by telephone
        and provide this number or login on our plattform. If you loose this number, we will not be
        able to provide your results. In your next consultation, you will receive a new ID and no
        follow-up will be possible.
      </div>
    </div>
    <div class="client-section-element">
      <div class="client-phone-question">
        <div class="client-phone-question-title">
          How would you like us to identify you for test results and follow-up?
        </div>
        <div class="client-option-item" :class="{ active: selectedConsentOption === 'yes' }">
          <RadioButton
            v-model="selectedConsentOption"
            inputId="phone-consent-yes"
            name="phone-consent"
            value="yes"
          />
          <label for="phone-consent-yes" class="client-option-label">
            Yes, you can save my mobile number and date of birth for those purposes
          </label>
        </div>
        <div v-if="showContactForm" class="client-phone-inputs">
          <div class="client-phone-input">
            <label for="client-phone-number">Phone Number</label>
            <InputText
              id="client-phone-number"
              v-model="phoneNumber"
              type="tel"
              placeholder="+41 79 123 45 67"
              class="text-input"
            />
          </div>
          <div class="client-phone-input">
            <label for="client-date-of-birth">Date of Birth</label>
            <InputText
              id="client-date-of-birth"
              v-model="dateOfBirth"
              type="date"
              class="text-input"
            />
          </div>
        </div>
        <div class="client-option-item" :class="{ active: selectedConsentOption === 'no' }">
          <RadioButton
            v-model="selectedConsentOption"
            inputId="phone-consent-no"
            name="phone-consent"
            value="no"
          />
          <label for="phone-consent-no" class="client-option-label">
            No, i will note my Questionnaire-ID and remain completely anonymous:
            <strong>{{ caseId }}</strong
            >. I will check www.stay-sure.ch/results in the following days.
          </label>
        </div>
      </div>
    </div>

    <div class="client-section-element" id="finalize-button-section">
      <div class="client-bottom-button-section">
        <Button class="button-extra-large" severity="primary" rounded
          >Finalize <IconRightArrow
        /></Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
#navi-top {
  display: flex;
  width: 100%;
  padding-top: 50px;
  padding-bottom: 30px;
  flex-direction: column;
  align-items: flex-start;
  gap: 20px;
  position: sticky;
  background-color: var(--color-ahs-white);
  z-index: 10;
  top: 0;
}

.client-phone-icon {
  height: 40px;
  width: 40px;
  align-items: center;
}

#phone-flex {
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: center;
  align-items: center;
  margin-bottom: 10%;
}

.client-phone-question {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.client-phone-question-title {
  font-weight: 700;
  font-size: 1rem;
}

.client-phone-inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-left: 1.5rem;
}

.client-phone-input {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 220px;
}

#finalize-button-section {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 50px;
  margin-top: 40px;
}
</style>
