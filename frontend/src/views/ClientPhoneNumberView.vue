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
import { useTexts } from '@/composables/useTexts'

const props = defineProps<{
  caseId: string
}>()

const { getText: t, formatText: f } = useTexts()
const translate = (slug: string) => t(slug).value

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
      errors['phonenumber'] = [{ message: translate('client-phone-error-required') }]
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
    error.value = translate('client-phone-error-invalid')
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
      ensureString(response.error.message) || translate('client-phone-error-verification')
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
    errorKey.value = ensureString(response.error?.message) || translate('client-phone-error-key')
    return
  }
  router.push({ name: 'client-done', params: { caseId: props.caseId } })
}
</script>

<template>
  <div class="client-form-view">
    <div class="client-section-element" id="navi-top">
      <ClientNavigationTop
        :section-title="t('client-phone-section-title').value"
        :sections="[]"
        :language-selector-only="true"
      />
    </div>
    <div class="client-section-element" id="phone-flex">
      <div class="client-phone-body">
        <p>
          {{ t('client-phone-lead-text') }}
        </p>
      </div>
      <div class="client-phone-icon">
        <IconPhone />
      </div>
      <div class="client-phone-subtitle">{{ t('client-phone-sms-header') }}</div>
      <div class="client-phone-body">
        {{ t('client-phone-sms-text') }}
      </div>
      <div class="client-phone-icon">
        <IconPen />
      </div>
      <div class="client-phone-subtitle">{{ t('client-phone-id-header') }}</div>
      <div class="client-phone-body">
        {{ t('client-phone-id-text') }}
      </div>
      <div class="client-phone-body">
        {{ t('client-phone-password-text') }}
      </div>
    </div>
    <div class="client-section-element client-phone-body">
      <div v-if="verified">
        <Message severity="info">
          {{
            f('client-phone-verification-success', [{ key: 'phone', value: phonenumberSent }])
          }}</Message
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
            {{ t('client-phone-identification-question') }}
          </div>
          <div class="client-option-item" :class="{ active: selectedConsentOption === 'allowed' }">
            <RadioButton
              v-model="selectedConsentOption"
              inputId="phone-consent-yes"
              name="phone-consent"
              value="allowed"
            />
            <label for="phone-consent-yes" class="client-option-label">
              {{ t('client-phone-consent-yes-label') }}
            </label>
          </div>
          <div v-if="showContactForm" class="client-phone-inputs">
            <div class="client-phone-input">
              <label for="client-phone-number">{{ t('client-phone-input-label') }}</label>
              <InputGroup>
                <InputText
                  id="client-phone-number"
                  v-model="phonenumber"
                  name="phonenumber"
                  type="tel"
                  :placeholder="t('client-phone-input-placeholder').value"
                  class="text-input"
                />
                <InputGroupAddon>
                  <Button
                    icon="pi pi-lock"
                    severity="primary"
                    @click="startVerification"
                    :disabled="(!!phonenumber && !$form.phonenumber?.valid) || remaining > 0"
                    :label="
                      remaining === 0
                        ? t('client-phone-verify-button').value
                        : f('client-phone-countdown-label', [
                            { key: 'seconds', value: remaining.toString() },
                          ]).value
                    "
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
              <label for="verification-code">{{
                f('client-phone-verification-code-label', [
                  { key: 'phone', value: phonenumberSent },
                ])
              }}</label>
              <InputGroup>
                <InputText
                  id="verification-code"
                  v-model="token"
                  class="text-input"
                  :placeholder="t('client-phone-verification-code-input').value"
                />

                <InputGroupAddon>
                  <Button severity="primary" variant="text" icon="pi pi-send" @click="onVerify" />
                </InputGroupAddon>
              </InputGroup>
              <section>
                <span>{{ t('client-phone-no-code-text') }}</span>
                <span v-if="remaining > 0">
                  {{
                    f('client-phone-resend-countdown', [
                      { key: 'seconds', value: remaining.toString() },
                    ])
                  }}
                </span>
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
              {{ t('client-phone-consent-no-text') }}
              <strong>{{ caseId }}</strong
              >. {{ t('client-phone-consent-no-followup') }}
            </label>
          </div>
        </div>
      </Form>
    </div>

    <div class="client-section-element client-phone-body" id="finalize-button-section">
      <Form v-if="canFinish" class="form-col" @submit="onSubmit" ref="$form">
        <p>
          {{ t('client-phone-key-description') }}
        </p>
        <label for="client-key" class="client-option-label">
          {{ t('client-phone-key-label') }}
        </label>
        <Password input-id="client-key" required name="key" :feedback="false" />

        <Message v-if="errorKey" severity="error" size="small" variant="outlined">{{
          errorKey
        }}</Message>
        <Button class="button-extra-large" severity="primary" rounded type="submit"
          >{{ t('client-phone-finalize-button') }}
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
