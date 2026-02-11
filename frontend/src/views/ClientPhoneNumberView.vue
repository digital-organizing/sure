<script setup lang="ts">
import ClientNavigationTop from '@/components/ClientNavigationTop.vue'
import IconPhone from '@/components/icons/IconPhone.vue'
import IconRightArrow from '@/components/icons/IconRightArrow.vue'
import { computed, onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import { InputText, useConfirm } from 'primevue'
import {
  sureApiConnectCase,
  sureApiResetCaseConnection,
  sureApiSendToken,
  sureApiSetCaseKey,
  type VisitLightSchema,
} from '@/client'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { formatDate, useCountdown } from '@vueuse/core'
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

const lastVisits = ref<VisitLightSchema[]>([])
const connectionId = ref<number | null>(null)
const hideReset = ref<boolean>(false)

const countdownSeconds = 0
const { remaining, start } = useCountdown(countdownSeconds, {
  onComplete() {},
  onTick() {},
})

const showContactForm = computed(() => {
  return selectedConsentOption.value === 'allowed'
})

// Check if there are unsaved changes that would be lost on page leave
const hasUnsavedChanges = computed(() => {
  // User has started the process but hasn't submitted the final form
  return verified.value && !formSubmitted.value
})

const formSubmitted = ref(false)

const canFinish = computed(() => {
  if (!selectedConsentOption.value) return false
  if (selectedConsentOption.value === 'allowed') {
    return verified.value
  }
  return true
})

const _resolver = ({ values }: { values: Record<string, unknown> }) => {
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

  // Add beforeunload listener to warn user before leaving/reloading the page
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

// Handler for browser close/reload
function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (hasUnsavedChanges.value) {
    e.preventDefault()
    // Modern browsers ignore custom messages but still show a generic warning
    return ''
  }
}

// Navigation guard for Vue Router navigation
onBeforeRouteLeave((to, from, next) => {
  if (hasUnsavedChanges.value) {
    const confirmLeave = window.confirm(translate('client-phone-unsaved-changes-warning'))
    if (confirmLeave) {
      next()
    } else {
      next(false)
    }
  } else {
    next()
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
  lastVisits.value = response.data.last_visits
  connectionId.value = response.data.connection_id

  nextTick(() => {
    document
      .getElementById('phone-success')
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

const confirm = useConfirm()

const confirmReset = () => {
  confirm.require({
    message: t('client-phone-reset-connection-confirmation').value,
    header: t('confirmation').value,
    icon: 'pi pi-exclamation-triangle',
    accept: () => {
      resetConnection()
    },
    reject: () => {
      /* no action */
    },
  })
}

async function resetConnection() {
  if (!connectionId.value) return
  const response = await sureApiResetCaseConnection({ path: { pk: props.caseId } })
  if (response.error) {
    error.value =
      ensureString(response.error.message) || translate('client-phone-error-reset-connection')
    return
  }
  lastVisits.value = response.data.last_visits
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
  formSubmitted.value = true
  const showCaseId = selectedConsentOption.value === 'not_allowed'
  router.push({
    name: 'client-done',
    params: { caseId: props.caseId },
    query: { showCaseId: String(showCaseId) },
  })
}

watch(selectedConsentOption, () => {
  // Scroll to contact form when option is selected

  nextTick(() => {
    const anchor = document.getElementById('contact-form-anchor')
    if (anchor) {
      anchor.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  })
})
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

      <Panel :toggleable="true" :collapsed="true" class="privacy-panel">
        <template #header>
          <h4>{{ t('privacy-header') }}</h4>
        </template>
        <div class="client-phone-body">
          <p v-html="r('client-phone-privacy')" class="health-info-text"></p>
          <br />
          <p v-html="r('client-phone-improving-health')" class="health-info-text"></p>
        </div>
      </Panel>

      <div class="client-phone-body">
        <p v-html="r('client-phone-identification-question')"></p>
      </div>

      <div
        class="choice-panel"
        :class="{
          active: selectedConsentOption == 'allowed',
          inactive: selectedConsentOption && selectedConsentOption != 'allowed',
        }"
        @click="selectedConsentOption = 'allowed'"
      >
        <div
          class="client-phone-icon"
          v-if="!selectedConsentOption || selectedConsentOption == 'allowed'"
        >
          <IconPhone />
        </div>
        <div class="client-phone-subtitle">{{ t('client-phone-sms-header') }}</div>
      </div>
      <div
        class="choice-panel"
        :class="{
          active: selectedConsentOption == 'not_allowed',
          inactive: selectedConsentOption && selectedConsentOption != 'not_allowed',
          disabled: verified,
        }"
        @click="selectedConsentOption = 'not_allowed'"
      >
        <div
          class="client-phone-icon"
          v-if="!selectedConsentOption || selectedConsentOption == 'not_allowed'"
        >
          <i class="pi pi-user" style="font-size: 40px"></i>
        </div>
        <div class="client-phone-subtitle">{{ t('client-phone-id-header') }}</div>
      </div>
    </div>

    <div class="scroll-anchor" id="contact-form-anchor"></div>

    <div
      class="client-section-element client-bottom-body client-form"
      v-if="showContactForm && !verified"
    >
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
            autocomplete="one-time-code"
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
        <p v-html="r('client-phone-sms-text')" class="info-disclaimer"></p>
      </Form>
    </div>
    <div class="client-section-element client-bottom-body" v-if="verified">
      <Message v-if="verified" severity="success" variant="outlined" class="msg" id="phone-success">
        {{
          f('client-phone-verification-success', [{ key: 'phone', value: phonenumberSent }]).value
        }}
      </Message>
    </div>

    <div class="client-section-element client-bottom-body client-form">
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

        <Button class="button-extra-large" severity="primary" rounded type="submit"
          >{{ t('client-phone-finalize-button') }}
          <IconRightArrow />
        </Button>

        <p
          class="info-disclaimer"
          v-if="!verified"
          v-html="f('client-phone-password-text', [{ key: 'caseId', value: caseId }], true).value"
        ></p>
      </Form>
    </div>

    <div
      class="client-section-element client-bottom-body confirm-last-visit"
      v-if="verified && lastVisits.length > 0 && !hideReset"
    >
      <Message variant="outlined" severity="contrast" class="msg">
        <h4>{{ t('client-phone-recent-visits-header') }}</h4>
        <p v-html="r('client-phone-recent-visits-text')"></p>
        <ul>
          <li
            v-for="(visit, idx) in lastVisits"
            :key="idx"
            v-html="
              f(
                'client-phone-recent-visit',
                [
                  { key: 'location', value: visit.location },
                  { key: 'date', value: formatDate(new Date(visit.created_at), 'DD.MM.YYYY') },
                ],
                true,
              ).value
            "
          ></li>
        </ul>
        <div class="actions">
          <Button
            @click="confirmReset"
            severity="primary"
            class="button"
            size="small"
            variant="outlined"
          >
            {{ t('client-phone-reset-connection-button') }}
          </Button>
          <Button @click="hideReset = true" severity="secondary" size="small" variant="outlined">
            {{ t('client-phone-keep-connection-button') }}
          </Button>
        </div>
      </Message>
    </div>
  </div>
</template>

<style scoped>
.p-inputgroup {
  width: 20rem;
}

.client-form {
  margin-top: 1rem;
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

#contact-form-anchor {
  margin-top: -100px;
  padding-bottom: 100px;
}

.info-disclaimer {
  font-size: 1rem;
  color: var(--color-ahs-gray-600);
  margin-top: 1rem;
}

.client-option-item {
  align-items: center;
}

.client-phone-subtitle {
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

.choice-panel {
  display: flex;
  min-width: min(400px, 100%);
  text-align: center;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  border: solid 2px black;
  padding: 2rem 3rem;
  border-radius: 25px;
  cursor: pointer;
  box-sizing: border-box;
  transition: all 0.3s ease;
}

.choice-panel.active {
  border-color: var(--color-ahs-red);
  color: var(--color-ahs-red);
  background-color: var(--color-ahs-primary-lightest);
}

.choice-panel.inactive {
  opacity: 0.6;
  border-color: var(--color-ahs-light-gray);
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
  margin-bottom: 4rem;
}
.button {
  margin-top: 1rem;
}

.msg {
  margin-top: 1rem;
  margin-bottom: 1rem;
}
.privacy-panel {
  width: 100%;
  margin-bottom: 1rem;
}
.actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}

.confirm-last-visit {
  margin-top: 2rem;
}

.disabled {
  pointer-events: none;
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
