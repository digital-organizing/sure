<script setup lang="ts">
import ClientLogoFooter from '@/components/ClientLogoFooter.vue';
import ClientLogoHeader from '@/components/ClientLogoHeader.vue'
import { useTexts } from '@/composables/useTexts'

const props = defineProps<{
  caseId: string
  showCaseId: boolean
}>()

const { getText: t } = useTexts()
</script>

<template>
  <div class="client-form-view">
    <div>
      <ClientLogoHeader :case-id="props.caseId" />
    </div>
    <div class="client-section-element" id="client-done-flex">
      <h1 class="client-h1" style="margin: 0">
        {{ t('client-done-title') }}
      </h1>
      <p class="client-body" style="margin: 0">
        {{ t('client-done-description') }}
      </p>
      <p v-if="showCaseId"  class="client-body" style="margin: 0">
        {{ t('client-done-note') }}
      </p>
      <p v-if="showCaseId"  id="client-done-caseid" style="margin: 0">
        {{ props.caseId }}
      </p>
    </div>
    <div id="client-welcome-ahs-logo-footer">
      <ClientLogoFooter/>
    </div>
  </div>
</template>

<style scoped>
.client-form-view {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
}

#client-done-flex {
  display: flex;
  padding-top: 30px;
  padding-bottom: 30px;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-top: 75px;
}

#client-done-caseid {
  text-align: center;
  font-size: 28px;
  font-style: normal;
  font-weight: 700;
  line-height: 24.5px;
}

#client-welcome-ahs-logo-footer {
  margin-top: auto;
}
</style>
