<script setup lang="ts">
import {
  sureApiGetCaseTagsOptions,
  sureApiListCases,
  type CaseFilters,
  type FilterData,
} from '@/client'
import { type PagedCaseListingSchema } from '@/client'
import { onMounted, ref, watch } from 'vue'
import StatusTag from '@/components/StatusTag.vue'
import { useStatus } from '@/composables/useStatus'
import { useDateFormat } from '@vueuse/core'
import { useLocations } from '@/composables/useLocations'
import { useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { useFilterStore } from '@/stores/filters'

const router = useRouter()

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return useDateFormat(date, 'YYYY-MM-DD HH:mm:ss').value
}

const page = ref<number>(1)

const loading = ref<boolean>(false)

const { statusChoices } = useStatus()
const { locations: locationChoices } = useLocations()
const tagChoices = ref<{ label: string; value: string[] }[]>([])

function fetchTagChoices() {
  // Placeholder for fetching tag choices
  sureApiGetCaseTagsOptions().then((response) => {
    if (response.data) {
      tagChoices.value = response.data.map((tag) => ({
        label: tag,
        value: [tag],
      }))
    }
  })
}

function fetchChoices() {
  fetchTagChoices()
}

fetchChoices()

const cases = ref<PagedCaseListingSchema>({
  items: [],
  count: 0,
})

const filterStore = useFilterStore()

const fetchCases = useDebounceFn(() => {
  console.log('Fetching cases with filters:', filterStore.filters)
  loading.value = true
  sureApiListCases({
    query: { page: page.value, page_size: 20 },
    body: filterStore.filters as CaseFilters,
  }).then((response) => {
    if (response.data) {
      cases.value = response.data
    }
    loading.value = false
  })
})

watch(page, () => {
  fetchCases()
})

function onPageChange(event: { page: number }) {
  page.value = event.page + 1
}

function onFilterChange() {
  fetchCases()
}

onMounted(async () => {
  fetchCases()
})

async function selectCase(event: { data: { case: string } }) {
  const caseId = event.data.case

  router.push({ name: 'consultant-case', params: { caseId } })
}
</script>

<template>
  <DataTable
    lazy
    :value="cases.items"
    paginator
    :rows="20"
    :total-records="cases.count"
    @page="onPageChange($event)"
    @filter="onFilterChange()"
    :loading="loading"
    v-model:filters="filterStore.filters"
    filter-display="menu"
    selection-mode="single"
    @row-select="selectCase"
  >
    <template #header>
      <div class="flex justify-end">
        <IconField>
          <InputIcon>
            <i class="pi pi-search" />
          </InputIcon>
          <InputText
            v-model="(filterStore.filters['search'] as unknown as FilterData).value as string"
            placeholder="Search by Case or Client ID"
            @input="onFilterChange"
          />
        </IconField>
      </div>
    </template>
    <Column field="case" header="Case" :show-filter-match-modes="false" :show-apply-button="false">
      <template #body="{ data }">
        {{ data.case }}
      </template>
      <template #filter="{ filterModel, filterCallback }">
        <InputText
          @input="filterCallback()"
          v-model="filterModel.value"
          type="text"
          placeholder="Search by case id"
        />
      </template>
    </Column>
    <Column
      field="external_id"
      header="Internal ID"
      :show-filter-match-modes="false"
      :show-apply-button="false"
    >
      <template #body="{ data }">
        {{ data.external_id }}
      </template>
      <template #filter="{ filterModel, filterCallback }">
        <InputText
          @input="filterCallback()"
          v-model="filterModel.value"
          type="text"
          placeholder="Search by internal id"
        />
      </template>
    </Column>
    <Column
      field="client_id"
      header="Client"
      :show-filter-match-modes="false"
      :show-apply-button="false"
    >
      <template #body="{ data }">
        {{ data.client_id }}
      </template>
      <template #filter="{ filterModel, filterCallback }">
        <InputText
          @input="filterCallback()"
          v-model="filterModel.value"
          type="text"
          placeholder="Search by client id"
        />
      </template>
    </Column>
    <Column field="tags" header="Tags" :show-filter-match-modes="false" :show-apply-button="false">
      <template #body="{ data }">
        <Tag
          v-for="tag in data.tags"
          :key="tag"
          :label="tag"
          :value="tag"
          rounded
          :severity="'secondary'"
        />
      </template>
      <template #filter="{ filterModel, filterCallback }">
        <Select
          v-model="filterModel.value"
          @change="filterCallback()"
          :options="tagChoices"
          :show-toggle-all="false"
          option-label="label"
          option-value="value"
        >
          <template #option="slotProps">
            <span><Tag :value="slotProps.option.label" /></span>
          </template>
        </Select>
      </template>
    </Column>
    <Column field="last_modified_at" header="Last Modified" data-type="date" v-if="false">
      <template #body="{ data }">
        {{ formatDate(data.last_modified_at) }}
      </template>
      <template #filter="{ filterModel }">
        <DatePicker
          v-model="filterModel.value"
          :show-icon="true"
          placeholder="Select date"
          date-format="yy-mm-dd"
        />
      </template>
    </Column>
    <Column field="created_at" header="Created At" data-type="date">
      <template #body="{ data }">
        {{ formatDate(data.created_at) }}
      </template>
      <template #filter="{ filterModel }">
        <DatePicker
          v-model="filterModel.value"
          :show-icon="true"
          placeholder="Select date"
          date-format="yy-mm-dd"
        />
      </template>
    </Column>
    <Column field="location" header="Location" :show-filter-match-modes="false">
      <template #body="{ data }">
        {{ data.location }}
      </template>
      <template #filter="{ filterModel }">
        <MultiSelect
          v-model="filterModel.value"
          :options="locationChoices"
          :show-toggle-all="false"
          option-label="name"
          option-value="id"
          type="text"
          placeholder="Search by location"
        />
      </template>
    </Column>
    <Column field="status" header="Status" :show-filter-match-modes="false" class="status">
      <template #body="{ data }">
        <StatusTag :value="data.status + ''" />
      </template>
      <template #filter="{ filterModel }">
        <MultiSelect
          v-model="filterModel.value"
          :options="statusChoices"
          :option-label="'label'"
          :option-value="'value'"
          :show-toggle-all="false"
        >
          <template #option="slotProps">
            <StatusTag :value="slotProps.option.value" rounded />
          </template>
        </MultiSelect>
      </template>
    </Column>
  </DataTable>
</template>
