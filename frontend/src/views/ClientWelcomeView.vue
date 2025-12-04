<script setup lang="ts">
import IconRightArrow from '@/components/icons/IconRightArrow.vue'
import IconClock from '@/components/icons/IconClock.vue'
import IconWorld from '@/components/icons/IconWorld.vue'
import ClientLogoHeader from '@/components/ClientLogoHeader.vue'
import router from '@/router'
import { useTexts } from '@/composables/useTexts'
import { computed, ref } from 'vue'

const props = defineProps<{
  caseId: string
}>()

const { getText: t, getAvailableLanguages, setLanguage, language: selectedLanguage } = useTexts()

function onStart() {
  router.push({ name: 'client-form', params: { caseId: props.caseId } })
}

const langMenu = ref()
const availableLanguages = ref<[string, string][]>([])
const currentLanguage = computed(() => selectedLanguage.value)

getAvailableLanguages().then((languages) => {
  if (!languages) return
  availableLanguages.value = languages
})

async function selectLanguage(lang: string) {
  if (currentLanguage.value === lang) return
  await setLanguage(lang)
}

const langMenuItems = computed(() =>
  availableLanguages.value.map(([code, name]) => ({
    label: name,
    ...(currentLanguage.value === code ? { icon: 'pi pi-check' } : {}),
    command: () => selectLanguage(code),
  })),
)

function toggleMenu(event: Event) {
  langMenu.value.toggle(event)
}
</script>

<template>
  <div class="client-form-view">
    <div id="client-logo-header">
      <ClientLogoHeader :case-id="props.caseId" />
    </div>
    <div class="client-section-element">
      <div id="client-welcome-flex">
        <h1 class="client-h1">
          {{ t('client-welcome-greeting') }}
        </h1>
        <p class="client-body">
          {{ t('client-welcome-text') }}
        </p>
        <Button
          class="button-extra-large"
          label="Start"
          severity="primary"
          size="large"
          icon="pi pi-right-arrow"
          :aria-label="t('client-welcome-start-button').value"
          rounded
          @click="onStart"
        >
          {{ t('client-welcome-start-button') }} <IconRightArrow />
        </Button>
      </div>
    </div>
    <div id="client-welcome-time-wrapper">
      <div id="client-welcome-time">
        <IconClock id="clock-icon" />
        <div>
          <p id="client-welcome-time-body">
            {{ t('client-welcome-time') }}
          </p>
        </div>
      </div>
    </div>
    <div id="client-welcome-ahs-logo-footer">
      <div class="client-welcome-footer-logo">
        <Button
          id="lang-btn"
          type="button"
          label="Language"
          severity="primary"
          @click="toggleMenu"
          aria-haspopup="true"
          aria-controls="overlay_menu"
          rounded
          ><IconWorld
        /></Button>
        <Menu ref="langMenu" id="overlay_menu" :model="langMenuItems" :popup="true" />
      </div>
      <div class="client-welcome-footer-logo">
        <img src="/logo.png" height="60px" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.client-welcome-footer-logo {
  width: 100%;
  padding: 0px 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.client-form-view {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
}

#client-welcome-flex {
  display: flex;
  padding-top: 30px;
  padding-bottom: 30px;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 20px;
}

#client-welcome-time {
  display: flex;
  width: 375px;
  height: 100px;
  padding: 30px 50px;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  flex-direction: row;
}

#clock-icon {
  width: 40px;
  height: 40px;
  aspect-ratio: 1/1;
  flex-shrink: 0;
}

#client-welcome-time-body {
  color: var(--color-ahs-black);
  font-size: 15px;
  font-style: normal;
  font-weight: 450;
  line-height: 20px;
}

#client-welcome-time-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
}

#client-welcome-ahs-logo-footer {
  margin-top: auto;
}

#lang-btn {
  height: 28.5px;
  padding: 5.25px 8.75px;
  /* margin-bottom: 20px; */
}
</style>
