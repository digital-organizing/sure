<script lang="ts" setup>
import { sureApiGetDocumentLink } from '@/client'
import { useCase } from '@/composables/useCase'
import { useTexts } from '@/composables/useTexts'
import { formatDate } from '@vueuse/core'
import { ref } from 'vue'

const { documents, uploadDocument, setDocumentHidden, visit } = useCase()
const { getText: t } = useTexts()

const fileName = ref('')
const fileupload = ref()
const hasFile = ref(false)

async function onUpload(event: unknown) {
  const file = (event as { files: File[] }).files[0]
  await uploadDocument(file, fileName.value)
  fileName.value = ''
  fileupload.value.clear()
}

async function triggerUpload() {
  fileupload.value.upload()
}

async function downloadDocument(id: number) {
  const link = await sureApiGetDocumentLink({
    path: { doc_pk: id, pk: visit.value!.case },
    body: { key: '' },
  })
  if (link.data) {
    window.open(link.data.link, '_blank')
  }
}

function onSelect(event: unknown) {
  hasFile.value = true
  if (fileName.value.length === 0) {
    const file = (event as { files: File[] }).files[0]
    fileName.value = file.name
  }
}
</script>

<template>
  <Panel
    :header="
      documents.length ? `${t('documents').value} (${documents.length})` : t('documents').value
    "
    toggleable
    collapsed
  >
    <div v-for="document in documents" :key="document.id!" class="document">
      <div class="info">
        <span class="link" @click="downloadDocument(document.id!)">
          {{ document.name }}
        </span>
        <span class="small"
          >{{ formatDate(new Date(document.uploaded_at), 'YYYY-MM-DD HH:mm') }} -
          {{ document.user.first_name }} {{ document.user.last_name }} ({{
            document.user.tenant
          }})</span
        >
      </div>
      <div class="actions">
        <label :for="'toggle_' + document.id!">{{
          document.hidden ? t('hidden') : t('visible')
        }}</label>
        <ToggleSwitch
          :input-id="'toggle_' + document.id!"
          :label="document.hidden ? t('hidden').value : t('visible').value"
          :model-value="!document.hidden"
          @update:model-value="(value: boolean) => setDocumentHidden(document.id!, !value)"
        />
      </div>
    </div>

    <div class="upload-row">
      <div class="input-row">
        <InputText v-model="fileName" :placeholder="t('give-file-name').value" />
        <FileUpload
          ref="fileupload"
          mode="basic"
          name="demo[]"
          @select="onSelect"
          @remove="hasFile = false"
          :custom-upload="true"
          :show-cancel-button="true"
          @uploader="onUpload"
        />
      </div>

      <Button
        :label="t('upload').value"
        @click="triggerUpload"
        :disabled="fileName.length == 0 || !hasFile"
      />
    </div>
    <Message severity="info" variant="simple" size="small">
      {{ t('document-upload-info') }}
    </Message>
  </Panel>
</template>

<style scoped>
.document {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  justify-content: space-between;
  margin-bottom: 0.3rem;
}
.input-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.link {
  text-decoration: underline;
  font-weight: bold;
  color: var(--text-color);
  cursor: pointer;
  margin-bottom: 0.3rem;
}

.small {
  font-size: 0.8rem;
  color: var(--color-ahs-dark-gray);
}

.info {
  display: flex;
  flex-direction: column;
}
</style>
