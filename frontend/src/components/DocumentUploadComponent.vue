<script lang="ts" setup>
import { sureApiGetDocumentLink } from '@/client';
import { useCase } from '@/composables/useCase';
import { ref } from 'vue';



const {documents, uploadDocument, setDocumentHidden, visit} = useCase();

const fileName = ref('');
const fileupload = ref();
const hasFile = ref(false);

async function onUpload(event: any) {
    console.log('upload event:');
    console.log(event);

    const file = event.files[0];

    await uploadDocument(file, fileName.value);
    fileName.value = '';
    fileupload.value.clear();
}

async function triggerUpload() {
    console.log('triggering upload', fileupload.value);
    fileupload.value.upload();
}

async function downloadDocument(id) {
    const link = await sureApiGetDocumentLink({path: {doc_pk: id, pk: visit.value!.case}, body: {key: ''}})
    if(link.data) {
        window.open(link.data.link, '_blank');
    }    
}

</script>

<template>
        <Panel :header="documents.length ? `Documents (${documents.length})` : 'Documents'" toggleable collapsed>
            <div v-for="document in documents" :key="document.id!" class="document">
                {{ document.name }}
                <div class="actions">
                    <label :for="'toggle_' + document.id!">{{ document.hidden ? 'Hidden' : 'Visible' }}</label>
                <ToggleSwitch
                    :input-id="'toggle_' + document.id!"
                    :label="document.hidden ? 'Hidden' : 'Visible'"
                    :model-value="!document.hidden"
                    @update:model-value="(value: boolean) => setDocumentHidden(document.id!,!value)"
                />
                <Button label="Download" @click="downloadDocument(document.id!)" size="small" variant="outlined" />
                </div>
            </div>
        
        <div class="upload-row">
            <div class="input-row">
        <InputText v-model="fileName" placeholder="Give the file a name"  />
        <FileUpload
            ref="fileupload"
            mode="basic"
            name="demo[]"
            @select="hasFile = true"
            @remove="hasFile = false"
            :custom-upload="true"
            :show-cancel-button="true"
            @uploader="onUpload"
            />
        </div>
    
        <Button label="Upload" @click="triggerUpload" :disabled="fileName.length==0 || !hasFile" />
        </div>

        </Panel>
</template>

<style scoped>
.document {
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.upload-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
    justify-content: space-between;
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
    
</style>