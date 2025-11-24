<script setup lang="ts">
import ClientNavigationTop from '@/components/ClientNavigationTop.vue'
import IconPhone from '@/components/icons/IconPhone.vue'
import IconPen from '@/components/icons/IconPen.vue'
import IconRightArrow from '@/components/icons/IconRightArrow.vue'
import { computed, onMounted, ref } from 'vue'
import { RadioButton, InputText } from 'primevue'
import { sureApiConnectCase, sureApiSendToken, sureApiSetCaseKey } from '@/client'
import { useRouter } from 'vue-router'
import { useCountdown } from '@vueuse/core'

const props = defineProps<{
  caseId: string
}>()

const router = useRouter()

const selectedConsentOption = ref<'allowed' | 'not_allowed' | null>(null)
const error = ref<string | null>(null)
const errorVerify = ref<string | null>(null)
const errorKey = ref<string | null>(null)

const phonenumber = ref<string>('')
const phonenumberSent = ref<string>('')
const showVerify = ref<boolean>(false)
const verified = ref<boolean>(false)
const token = ref<string>('')

const countdownSeconds = 0
const { remaining, start } = useCountdown(countdownSeconds, {
  onComplete() {},
  onTick() {},
})

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

function ensureString(v: string | string[] | null | undefined): string {
  if (!v) return ''
  if (Array.isArray(v)) {
    return v[0] || ''
  }
  return v
}

async function startVerification() {
  error.value = null
  const response = await sureApiSendToken({
    body: { phone_number: phonenumber.value },
    path: { pk: props.caseId },
  })
  if (response.error) {
    error.value = ensureString(response.error?.message)
    return
  }
  if (response.response.status !== 200) {
    error.value = 'Invalid phone number. Please check and try again.'
    return
  }
  phonenumberSent.value = ensureString(response.data?.message)
  start(90)
  showVerify.value = true
}

async function onVerify() {
  if (!token.value || token.value.trim() === '' || selectedConsentOption.value !== 'allowed') return
  error.value = null

  const response = await sureApiConnectCase({
    path: { pk: props.caseId },
    body: {
      phone_number: phonenumber.value,
      token: token.value,
      consent: selectedConsentOption.value,
    },
  })
  if (response.error) {
    errorVerify.value =
      ensureString(response.error.message) || 'An error occurred during verification.'
    return
  }
  showVerify.value = false
  verified.value = true
}

async function onSubmit(e: { valid: boolean; values: Record<string, unknown> }) {
  if (!e.valid) return
  const key = e.values.key as string
  const response = await sureApiSetCaseKey({ path: { pk: props.caseId }, body: { key } })
  if (response.error && !response.error?.success) {
    errorKey.value =
      ensureString(response.error?.message) || 'An error occurred while setting the key.'
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
          We process your personal data solely to provide you with our consultation. Your personal
          data is stored only for the duration of the consultation and for no longer than three
          months.
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
    <div class="client-section-element client-phone-body">
      <div v-if="verified">
        <Message severity="info"
          >Your phone number ({{ phonenumberSent }}) has been verified successfully.</Message
        >
      </div>
      <Form
        :resolver="resolver"
        :validate-on-blur="true"
        v-slot="$form"
        @submit="onSubmit"
        v-if="!verified"
      >
        <div class="client-phone-question">
          <div class="client-phone-question-title">
            How would you like us to identify you for test results and follow-up?
          </div>
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
                <InputGroupAddon>
                  <Button
                    icon="pi pi-lock"
                    severity="primary"
                    @click="startVerification"
                    :disabled="(!!phonenumber && !$form.phonenumber?.valid) || remaining > 0"
                    :label="remaining === 0 ? 'Verify' : remaining + 's'"
                    variant="text"
                    size="large"
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
              <Message v-if="error" severity="error" size="small" variant="simple">{{
                error
              }}</Message>
            </div>
            <div v-if="showVerify" class="client-phone-input">
              <label for="verification-code"
                >Enter the Verification Code sent to {{ phonenumberSent }}</label
              >
              <InputGroup>
                <InputText
                  id="verification-code"
                  label="Enter the verification code sent to your phone"
                  v-model="token"
                  class="text-input"
                />

                <InputGroupAddon>
                  <Button severity="primary" variant="text" icon="pi pi-send" @click="onVerify" />
                </InputGroupAddon>
              </InputGroup>
              <section>
                <span
                  >If you did not receive the code, please check your phone number and try again.
                </span>
                <span v-if="remaining > 0"
                  >You can request a new code in {{ remaining }} seconds.</span
                >
              </section>
              <Message v-if="errorVerify" severity="error" size="small">{{ errorVerify }}</Message>
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
      </Form>
    </div>

    <div class="client-section-element client-phone-body" id="finalize-button-section">
      <Form v-if="canFinish" class="form-col" @submit="onSubmit" ref="$form">
        <p>
          To protect your results, please set a secure key below. You will need this key to access
          your test results and for any follow-up consultations. You can use the password manager of
          your browser or smartphone to generate and store a secure key.
        </p>
        <label for="client-key" class="client-option-label"> Your secure key </label>
        <Password input-id="client-key" required name="key" :feedback="false" />

        <Message v-if="errorKey" severity="error" size="small" variant="outlined">{{
          errorKey
        }}</Message>
        <Button class="button-extra-large" severity="primary" rounded type="submit"
          >Finalize
          <IconRightArrow />
        </Button>
      </Form>
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
  margin-bottom: 2rem;
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
  margin-top: 1rem;
}
</style>
