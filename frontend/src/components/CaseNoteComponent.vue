<script setup lang="ts">
import { useCase } from '@/composables/useCase';
import { Textarea } from 'primevue';
import { ref } from 'vue';


const { notes, createCaseNote, setCaseNoteHidden } = useCase()
const text = ref('');

</script>

<template>
    <Panel header="Case Notes" toggleable collapsed>
        <section v-for="note in notes" :key="note.id!" class="note">
            <p>
                {{ note.note }}
            </p>
            <div class="actions">
                <ToggleSwitch :model-value="!note.hidden"
                    @update:model-value="(value: boolean) => setCaseNoteHidden(note.id!, !value)" />
                <label>{{ !note.hidden ? 'Visible' : 'Hidden' }}</label>
            </div>
        </section>
        <div class="form-row">
            <Textarea v-model="text" placeholder="Add a new note..." rows="5" cols="33" :auto-resize="true" />
            <Button class="button" label="Add Note" @click="createCaseNote(text); text = ''" :disabled="text.length == 0" />
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
    align-items: flex-start;
}

.note p {
    margin: 0;
}

.actions {
    display: flex;
    gap: 0.5rem;
    flex-direction: column;
}
</style>