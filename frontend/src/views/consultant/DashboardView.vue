<script setup lang="ts">
import { sureApiGetCaseTagsOptions, sureApiListCases, type CaseFilters } from '@/client'
import { type PagedCaseListingSchema } from '@/client'
import type { DataTableFilterMeta } from 'primevue/datatable'
import { FilterMatchMode, FilterOperator } from '@primevue/core/api'
import { onMounted, ref, watch } from 'vue'
import StatusTag from '@/components/StatusTag.vue'
import { useStatus } from '@/composables/useStatus'
import { useDateFormat } from '@vueuse/core'
import { useLocations } from '@/composables/useLocations'
import { useRouter } from 'vue-router'

const router = useRouter()

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return useDateFormat(date, 'YYYY-MM-DD HH:mm:ss').value
}

const page = ref<number>(1)

const loading = ref<boolean>(false)

const { statusChoices } = useStatus()
const { locations: locationChoices } = useLocations()
const tagChoices = ref<string[]>([])

function fetchTagChoices() {
  // Placeholder for fetching tag choices
  sureApiGetCaseTagsOptions().then((response) => {
    if (response.data) {
      tagChoices.value = response.data
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

const filters = ref<DataTableFilterMeta>({
  case: { value: null, matchMode: 'contains' },
  client_id: { value: null, matchMode: 'contains' },
  tags: { value: null, matchMode: FilterMatchMode.CONTAINS },
  location: { operator: FilterOperator.OR, constraints: [{ value: null, matchMode: 'equals' }] },
  status: { value: null, matchMode: 'in' },
  last_modified_at: {
    operator: FilterOperator.AND,
    constraints: [{ value: null, matchMode: FilterMatchMode.DATE_AFTER }],
  },
})

function fetchCases() {
  loading.value = true
  sureApiListCases({
    query: { page: page.value, page_size: 2 },
    body: filters.value as CaseFilters,
  }).then((response) => {
    if (response.data) {
      cases.value = response.data
    }
    loading.value = false
  })
}

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
    :rows="2"
    :total-records="cases.count"
    @page="onPageChange($event)"
    @filter="onFilterChange()"
    :loading="loading"
    v-model:filters="filters"
    filter-display="menu"
    selection-mode="single"
    @row-select="selectCase"
  >
    <Column field="case" header="Case" :show-filter-match-modes="false">
      <template #body="{ data }">
        {{ data.case }}
      </template>
      <template #filter="{ filterModel }">
        <InputText v-model="filterModel.value" type="text" placeholder="Search by case id" />
      </template>
    </Column>
    <Column field="client_id" header="Client" :show-filter-match-modes="false">
      <template #body="{ data }">
        {{ data.client_id }}
      </template>
      <template #filter="{ filterModel }">
        <InputText v-model="filterModel.value" type="text" placeholder="Search by client id" />
      </template>
    </Column>
    <Column field="tags" header="Tags" :show-filter-match-modes="false">
      <template #body="{ data }">
        <Tag
          v-for="tag in data.tags"
          :key="tag"
          :label="tag"
          :value="tag"
          rounded
          :severity="'info'"
        />
      </template>
      <template #filter="{ filterModel }">
        <MultiSelect v-model="filterModel.value" :options="tagChoices" :show-toggle-all="false">
          <template #option="slotProps">
            <span>{{ slotProps.option }}</span>
          </template>
        </MultiSelect>
      </template>
    </Column>
    <Column field="last_modified_at" header="Last Modified" data-type="date">
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
    <Column field="location" header="Location">
      <template #body="{ data }">
        {{ data.location }}
      </template>
      <template #filter="{ filterModel }">
        <Select
          v-model="filterModel.value"
          :options="locationChoices"
          option-label="name"
          option-value="id"
          type="text"
          placeholder="Search by location"
        />
      </template>
    </Column>
    <Column field="status" header="Status" :show-filter-match-modes="false">
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
