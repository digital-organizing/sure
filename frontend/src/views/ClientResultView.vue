<script setup lang="ts">
import ClientLogoHeader from '@/components/ClientLogoHeader.vue'
import ClientNavigationTop from '@/components/ClientNavigationTop.vue'
import ClientResult from '@/components/ClientResult.vue'
import { useResults } from '@/composables/useResults'
import { useTexts } from '@/composables/useTexts'
import { InputGroup, InputGroupAddon, InputMask, Password } from 'primevue'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const { getText: t } = useTexts()

const key = ref('')
const caseId = ref('')

const showPasswordHelp = ref(false)

const { caseFetched, fetchCase, error } = useResults()

onMounted(() => {
  const query = route.query['case']
  if (query && typeof query === 'string') {
    caseId.value = query.replace('SUF-', '')
  } else {
    const storedCaseId = sessionStorage.getItem('client_case_id')
    const storedCaseKey = sessionStorage.getItem('client_case_key')

    if (storedCaseId && storedCaseKey) {
      caseId.value = storedCaseId
      key.value = storedCaseKey
      fetchCase(storedCaseId, storedCaseKey)
    }
  }
})

async function onFetchCase() {
  sessionStorage.setItem('client_case_id', caseId.value)
  sessionStorage.setItem('client_case_key', key.value)

  await fetchCase(caseId.value, key.value)
}
</script>

<template>
  <article>
    <img src="/sure_logo_C.png" v-if="!caseFetched" />
    <ClientLogoHeader v-if="caseFetched" :caseId="caseId" />
    <ClientNavigationTop
      :languageSelectorOnly="true"
      :sectionTitle="t('access-your-results').value"
      :sections="[]"
    />
    <section v-if="!caseFetched">
      <form class="form-col">
        <div class="form-row">
          <label for="caseId">{{ t('case-id') }}</label>
          <InputGroup>
            <InputGroupAddon>SUF-</InputGroupAddon>
            <InputMask
              autocomplete="off"
              data-1p-ignore
              data-bwignore
              data-lpignore="true"
              data-form-type="other"
              :auto-clear="false"
              id="caseId"
              v-model="caseId"
              mask="*******"
            ></InputMask>
          </InputGroup>
        </div>
        <div class="form-row">
          <label for="key">{{ t('access-key') }}</label>
          <Password
            id="key"
            v-model="key"
            :placeholder="t('enter-access-key').value"
            :feedback="false"
            fluid
          ></Password>
        </div>
        <Button :label="t('show-results').value" @click="onFetchCase"></Button>
        <Button
          :label="t('password-forgotten').value"
          severity="secondary"
          @click="showPasswordHelp = true"
          v-if="!showPasswordHelp"
        />
        <Message v-if="error" :severity="'error'">{{ error }}</Message>
      </form>
    </section>
    <section v-else>
      <ClientResult :caseId="caseId" :caseKey="key" />
    </section>
    <Message v-if="showPasswordHelp" :closable="true" @close="showPasswordHelp = false">
      {{ t('client-password-forgotten-info').value }}
    </Message>

    <Button
      class="back"
      :label="t('back').value"
      severity="secondary"
      @click="caseFetched = false"
      v-if="caseFetched"
    ></Button>
  </article>
</template>

<style scoped>
article {
  max-width: 600px;
  flex-direction: column;
  margin: auto;
  display: flex;
  gap: 1rem;
  padding-left: 5px;
  padding-right: 5px;
}
img {
  display: block;
  margin: 1rem auto;
  max-height: 100px;
  max-width: 80%;
}
.back {
  align-self: flex-start;
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  width: 100%;
}
</style>
