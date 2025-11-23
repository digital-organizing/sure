<script setup lang="ts">
import ClientNavigationTop from '@/components/ClientNavigationTop.vue'
import IconPhone from '@/components/icons/IconPhone.vue'
import IconPen from '@/components/icons/IconPen.vue'
import IconRightArrow from '@/components/icons/IconRightArrow.vue'
import { computed, onMounted, ref } from 'vue'
import { RadioButton, InputText } from 'primevue'
import { sureApiConnectCase, sureApiSendToken, sureApiSetCaseKey } from '@/client'
import { useRouter } from 'vue-router'

const props = defineProps<{
  caseId: string
}>()

const router = useRouter()

const selectedConsentOption = ref<'allowed' | 'not_allowed' | null>(null)
const error = ref<string | null>(null)

const phonenumber = ref<string>('')
const showVerify = ref<boolean>(false)
const verified = ref<boolean>(false)
const token = ref<string>('')

const showContactForm = computed(() => {
  console.log('Selected consent option:', selectedConsentOption.value)
  return selectedConsentOption.value === 'allowed'
})

const canFinish = computed(() => {
  if (!selectedConsentOption.value) return false
  if (selectedConsentOption.value === 'allowed') {
    return verified.value
  }
  return true
})

const resolver = ({ values }: { values: Record<string, unknown> }) => {
  const errors: Record<string, { message: string }[]> = {}
  if (!values.key || (typeof values.key === 'string' && values.key.trim() === '')) {
    errors['key'] = [{ message: 'Secure key is required.' }]
  }
  if (selectedConsentOption.value === 'allowed') {
    if (
      !values.phonenumber ||
      (typeof values.phonenumber === 'string' && values.phonenumber.trim() === '')
    ) {
      errors['phonenumber'] = [{ message: 'Please enter your phone number.' }]
    }
  }
  return {
    errors,
    values,
  }
}

onMounted(() => {
  const savedId = localStorage.getItem('clientFormCaseId')
  if (savedId !== props.caseId) {
    localStorage.setItem('clientFormCaseId', props.caseId)
    localStorage.setItem('clientFormIndex', '0')
  }
})

async function startVerification() {
  error.value = null
  const response = await sureApiSendToken({
    body: { phone_number: phonenumber.value },
    path: { pk: props.caseId },
  })
  if (response.error && !response.error?.success) {
    if (Array.isArray(response.error?.message)) {
      error.value = response.error?.message.join(', ')
    } else {
      error.value = response.error?.message || 'An error occurred while sending the token.'
    }
    return
  }
  showVerify.value = true
}

async function onVerify() {
  if (!token.value || token.value.trim() === '' || selectedConsentOption.value !== 'allowed') return
  error.value = null

  await sureApiConnectCase({
    path: { pk: props.caseId },
    body: {
      phone_number: phonenumber.value,
      token: token.value,
      consent: selectedConsentOption.value,
    },
  }).then((response) => {
    if (!response.data?.success) {
      if (Array.isArray(response.data?.message)) {
        error.value = response.data?.message.join(', ')
      } else {
        error.value = response.data?.message || 'An error occurred while verifying the token.'
      }
      return
    }
    // Successfully connected
  })

  showVerify.value = false
  verified.value = true
}

async function onSubmit(e: { valid: boolean; values: Record<string, unknown> }) {
  if (!e.valid) return
  const key = e.values.key as string
  const response = await sureApiSetCaseKey({ path: { pk: props.caseId }, body: { key } })
  if (response.error && !response.error?.success) {
    error.value = response.error?.warnings?.join(', ') || 'An error occurred while setting the key.'
    return
  }
  router.push({ name: 'client-done', params: { caseId: props.caseId } })
}
</script>

<template>
  <div class="client-form-view">
    <div class="client-section-element" id="navi-top">
      <ClientNavigationTop
        :section-title="'Privacy'"
        :sections="[]"
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
      <div class="client-phone-subtitle">Mobile phone number & key</div>
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
        and provide this number or login on our platform. If you lose this number, we will not be
        able to provide your results. In your next consultation, you will receive a new ID and no
        follow-up will be possible.
      </div>
      <div class="client-phone-body">
        In both cases you need to provide a secure key to access your data. Please choose a key that
        you can easily remember but is difficult for others to guess (e.g. a combination of letters,
        numbers, and special characters). You can also use the password manager of your browser or
        smartphone to generate and store a secure key.
      </div>
    </div>
    <Form :resolver="resolver" :validate-on-blur="true" v-slot="$form" @submit="onSubmit">
      <div class="client-section-element">
        <div class="client-phone-question">
          <div class="client-phone-question-title">
            How would you like us to identify you for test results and follow-up?
          </div>
          <FloatLabel>
            <Password input-id="client-key" required name="key" />
            <label for="client-key" class="client-option-label"> Your secure key </label>
          </FloatLabel>
          <Message v-if="$form.key?.error" severity="error" size="small" variant="simple">{{
            $form.key.error.message
          }}</Message>
          <div class="client-option-item" :class="{ active: selectedConsentOption === 'allowed' }">
            <RadioButton
              v-model="selectedConsentOption"
              inputId="phone-consent-yes"
              name="phone-consent"
              value="allowed"
            />
            <label for="phone-consent-yes" class="client-option-label">
              You can send me a link for my results to my mobile phone number:
            </label>
          </div>
          <div v-if="showContactForm" class="client-phone-inputs">
            <div class="client-phone-input">
              <label for="client-phone-number">Phone Number</label>
              <InputGroup>
                <InputText
                  id="client-phone-number"
                  v-model="phonenumber"
                  name="phonenumber"
                  type="tel"
                  placeholder="+41 79 123 45 67"
                  class="text-input"
                />
                <InputGroupAddon position="append">
                  <Button
                    icon="pi pi-lock"
                    severity="primary"
                    @click="startVerification"
                    :disabled="!!phonenumber && !$form.phonenumber?.valid"
                    label="Verify"
                  >
                  </Button>
                </InputGroupAddon>
              </InputGroup>
              <Message
                v-if="$form.phonenumber?.invalid"
                severity="error"
                size="small"
                variant="simple"
                >{{ $form.phonenumber.error.message }}</Message
              >
            </div>
            <div v-if="showVerify" class="client-phone-input">
              <label for="verification-code">Enter the Verification Code</label>
              <InputGroup>
                <InputText
                  id="verification-code"
                  label="Enter the verification code sent to your phone"
                  v-model="token"
                />

                <InputGroupAddon>
                  <Button label="Submit Code" severity="primary" @click="onVerify" />
                </InputGroupAddon>
              </InputGroup>
            </div>
          </div>
          <div
            class="client-option-item"
            :class="{ active: selectedConsentOption === 'not_allowed' }"
          >
            <RadioButton
              v-model="selectedConsentOption"
              inputId="phone-consent-no"
              name="phone-consent"
              value="not_allowed"
            />
            <label for="phone-consent-no" class="client-option-label">
              No, i will note my Questionnaire-ID and remain completely anonymous:
              <strong>{{ caseId }}</strong
              >. I will check www.stay-sure.ch/results in the following days.
            </label>
          </div>
        </div>
      </div>
      <Message v-if="error" severity="error" size="small" variant="outlined">{{ error }}</Message>

      <div class="client-section-element" id="finalize-button-section">
        <div class="client-bottom-button-section">
          <Button
            class="button-extra-large"
            severity="primary"
            rounded
            type="submit"
            v-if="canFinish && $form.valid"
            >Finalize <IconRightArrow
          /></Button>
        </div>
      </div>
    </Form>
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
