<script lang="ts" setup>
import { sureApiListCaseReportForms, type AvailableReportFormSchema } from '@/client'
import { useCase } from '@/composables/useCase'
import { useTexts } from '@/composables/useTexts'
import { onMounted, ref } from 'vue'

const props = defineProps<{ caseId: string }>()

const { getText: t, onLanguageChange } = useTexts()
const { onCaseRefresh } = useCase()

const reportForms = ref<AvailableReportFormSchema[]>([])

async function fetchReportForms() {
  const response = await sureApiListCaseReportForms({ path: { pk: props.caseId } })
  reportForms.value = response.data ?? []
}

function buttonLabel(form: AvailableReportFormSchema, language: string) {
  // The language only tells versions of the same form apart.
  return form.languages.length > 1 ? `${form.name} (${language.toUpperCase()})` : form.name
}

function reportUrl(formId: number, language: string) {
  return `/api/sure/case/${encodeURIComponent(props.caseId)}/reports/${formId}/${language}/`
}

onMounted(() => {
  fetchReportForms()
  onCaseRefresh(fetchReportForms)
  onLanguageChange(fetchReportForms)
})
</script>

<template>
  <section v-if="reportForms.length > 0" class="report-forms">
    <h4>{{ t('report-forms') }}</h4>
    <p>{{ t('report-forms-info') }}</p>
    <div class="buttons">
      <template v-for="form in reportForms" :key="form.id">
        <Button
          v-for="language in form.languages"
          :key="`${form.id}-${language}`"
          as="a"
          :href="reportUrl(form.id, language)"
          target="_blank"
          rel="noopener"
          icon="pi pi-file-pdf"
          :label="buttonLabel(form, language)"
          size="small"
          severity="secondary"
        />
      </template>
    </div>
  </section>
</template>

<style scoped>
.buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
