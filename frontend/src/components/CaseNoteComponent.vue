<script setup lang="ts">
import { useCase } from '@/composables/useCase'
import { useTexts } from '@/composables/useTexts'
import { formatDate } from '@vueuse/core'
import { Textarea } from 'primevue'
import { ref } from 'vue'

const { notes, createCaseNote, setCaseNoteHidden } = useCase()
const text = ref('')

const { getText: t } = useTexts()
function onCreate() {
  createCaseNote(text.value)
  text.value = ''
}
</script>

<template>
  <Panel :header="t('case-notes').value" toggleable collapsed>
    <section v-for="note in notes" :key="note.id!" class="note">
      <div>
        <p>
          {{ note.note }}
        </p>
        <p class="small">
          {{ formatDate(new Date(note.created_at), 'YYYY-MM-DD HH:mm') }} -
          {{ note.user.first_name }} {{ note.user.last_name }} ({{ note.user.tenant }})
        </p>
      </div>
      <div class="actions">
        <ToggleSwitch
          :model-value="!note.hidden"
          @update:model-value="(value: boolean) => setCaseNoteHidden(note.id!, !value)"
        />
        <label>{{ !note.hidden ? t('visible') : t('hidden') }}</label>
      </div>
    </section>
    <div class="form-row">
      <div class="field">
        <Textarea
          v-model="text"
          :placeholder="t('add-note-placeholder').value"
          rows="5"
          cols="33"
          :auto-resize="true"
        />
        <Message severity="info" variant="simple" size="small">
          {{ t('case-note-info') }}
        </Message>
      </div>
      <Button
        class="button"
        :label="t('add-note').value"
        @click="onCreate"
        :disabled="text.length == 0"
      />
    </div>
  </Panel>
</template>

<style scoped>
.form-row {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}
.form-row .field {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.button {
  align-self: flex-end;
}

.note {
  border-bottom: 1px solid var(--color-ahs-light-gray);
  padding: 0.8rem;
  margin-bottom: 0.5rem;
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: stretch;
}
.note div {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.note p {
  margin: 0;
}

.actions {
  display: flex;
  gap: 0.5rem;
  flex-direction: column;
}
.small {
  font-size: 0.8rem;
  color: var(--color-ahs-dark-gray);
  margin-top: 0.3rem;
}
</style>
