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

const { getText: t, language, formatText: f, render: r } = useTexts()
const translate = (slug: string) => t(slug).value

const router = useRouter()

const selectedConsentOption = ref<'allowed' | 'not_allowed' | null>(null)
const error = ref<string | null>(null)
const errorVerify = ref<string | null>(null)
const errorKey = ref<string | null>(null)

const showPassword = ref<boolean>(false)

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
  }).catch(() => {
    error.value = translate('client-phone-error-network')
    return { error: { message: '' } }
  })
  if (response.error) {
    error.value = translate('client-phone-error-invalid')
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
  const response = await sureApiSetCaseKey({
    path: { pk: props.caseId },
    body: { key },
    query: { lang: language.value },
  })
  if (response.error && !response.error?.success) {
    errorKey.value = ensureString(response.error?.message) || translate('client-phone-error-key')
    return
  }
  const showCaseId = selectedConsentOption.value === 'not_allowed'
  router.push({
    name: 'client-done',
    params: { caseId: props.caseId },
    query: { showCaseId: String(showCaseId) },
  })
}
</script>

<template>
  <div class="client-form-view">
    {{ error }}
    <div class="client-section-element" id="navi-top">
      <ClientNavigationTop
        :section-title="t('client-phone-section-title').value"
        :sections="[]"
        :language-selector-only="true"
      />
    </div>
    <div class="client-section-element" id="phone-flex">
      <div class="client-phone-body">
        <p v-html="r('client-phone-lead-text')"></p>
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
        {{ t('client-phone-password-text') }}
      </div>
    </div>
    <div class="client-section-element client-phone-body">
      <Form :resolver="resolver" :validate-on-blur="true" @submit="onSubmit" v-if="!verified">
        <div class="client-phone-question">
          <h3 class="client-phone-question-title">
            {{ t('client-phone-identification-question') }}
          </h3>
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
              <span
                v-html="
                  f('client-phone-consent-no-text', [{ key: 'caseId', value: caseId }], true).value
                "
              ></span>
            </label>
          </div>
        </div>
      </Form>
    </div>

    <div class="client-section-element client-bottom-body" v-if="showContactForm && !verified">
      <Form v-slot="$form" class="form-col">
        <p>
          {{ t('client-phone-input-description') }}
        </p>
        <label for="client-phone-number">{{ t('client-phone-input-label') }}</label>
        <InputText
          id="client-phone-number"
          v-model="phonenumber"
          name="phonenumber"
          type="tel"
          :placeholder="t('client-phone-input-placeholder').value"
          class="text-input"
        />

        <Message v-if="$form.phonenumber?.invalid" severity="error" size="small" variant="simple">{{
          $form.phonenumber.error.message
        }}</Message>
        <Message v-if="error" severity="error" size="small" variant="simple">{{ error }}</Message>
        <Button
          icon="pi pi-lock"
          severity="primary"
          class="btn-inline"
          @click="startVerification"
          :disabled="(!!phonenumber && !$form.phonenumber?.valid) || remaining > 0"
          :label="
            remaining === 0
              ? t('client-phone-verify-button').value
              : f('client-phone-countdown-label', [{ key: 'seconds', value: remaining.toString() }])
                  .value
          "
        >
        </Button>
        <div v-if="showVerify" class="client-phone-input form-col">
          <label for="verification-code">{{
            f('client-phone-verification-code-label', [{ key: 'phone', value: phonenumberSent }])
          }}</label>
          <InputText
            id="verification-code"
            v-model="token"
            class="text-input"
            autocomplete="tel"
            :placeholder="t('client-phone-verification-code-input').value"
          />

          <Button
            severity="primary"
            icon="pi pi-send"
            @click="onVerify"
            :label="t('submit').value"
          />
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
      </Form>
    </div>

    <div class="client-section-element client-bottom-body">
      <Message v-if="verified" severity="success" size="small" variant="outlined" class="msg">
        {{
          f('client-phone-verification-success', [{ key: 'phone', value: phonenumberSent }]).value
        }}
      </Message>
      <Form v-if="canFinish" class="form-col form-key" @submit="onSubmit" ref="$form">
        <p
          v-if="!verified"
          v-html="f('client-phone-case-id', [{ key: 'caseId', value: caseId }], true).value"
        ></p>
        <p>
          {{ t('client-phone-key-description') }}
        </p>
        <label for="client-key" class="client-option-label">
          {{ t('client-phone-key-label') }}
        </label>
        <InputGroup>
          <InputText
            :type="showPassword ? 'text' : 'password'"
            autocomplete="new-password"
            input-id="client-key"
            required
            name="key"
          />
          <InputGroupAddon>
            <Button
              :icon="showPassword ? 'pi pi-eye-slash' : 'pi pi-eye'"
              :severity="'secondary'"
              variant="text"
              @click="showPassword = !showPassword"
            />
          </InputGroupAddon>
        </InputGroup>

        <Message v-if="errorKey" severity="error" size="small" variant="outlined">{{
          errorKey
        }}</Message>

        <section v-html="r('client-phone-privacy')" class="health-info-text"></section>
        <section v-html="r('client-phone-improving-health')" class="health-info-text"></section>

        <Button class="button-extra-large" severity="primary" rounded type="submit"
          >{{ t('client-phone-finalize-button') }}
          <IconRightArrow />
        </Button>
      </Form>
    </div>
  </div>
</template>

<style scoped>
.p-inputgroup {
  width: 20rem;
}

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

.client-option-item {
  align-items: center;
}

.client-phone-subtitle {
  color: var(--color-ahs-black);
  font-family: 'Circular Std';
  font-size: 18px;
  font-style: normal;
  font-weight: 700;
  line-height: 24.5px;
}

.button-extra-large {
  display: flex;
  width: 207px;
  height: 49.975px;
  padding: 13.977px 19.568px;
  justify-content: center;
  align-items: center;
  gap: 11.182px;
  aspect-ratio: 207/49.98;
  font-size: 24px;
  font-weight: 700;
  font-family: 'Circular Std';
  line-height: normal;
}

.client-section-element {
  font-size: 18px;
  gap: 12px;
  display: flex;
  flex-direction: column;
}

p {
  margin: 0;
}

.client-phone-body {
  margin-bottom: 1rem;
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
  justify-content: center;
  align-items: center;
  margin-bottom: 1rem;
}

.client-phone-question {
  display: flex;
  flex-direction: column;
}

.client-phone-question-title {
  font-weight: 700;
  font-size: 1.2rem;
}

.client-phone-inputs {
  display: flex;
  flex-wrap: wrap;
  margin-left: 1.5rem;
}

.client-phone-input {
  display: flex;
  flex-direction: column;
  min-width: 220px;
}

.health-info-text:first-of-type {
  margin-top: 1rem;
}

.health-info-text:last-of-type {
  margin-bottom: 1rem;
}

.health-info-text {
  font-size: 1rem;
  line-height: 1.2;
  color: var(--color-ahs-gray-700);
}

.client-section-element:last-child {
  margin-bottom: 8rem;
}
.button {
  margin-top: 1rem;
}

.p-inputtext {
  min-width: 20rem;
}
.msg {
  margin-bottom: 1rem;
}
</style>
