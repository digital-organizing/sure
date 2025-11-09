<script setup lang="ts">
import { sureApiListCases } from '@/client'
import { type PagedCaseListingSchema } from '@/client'
import type { DataTableFilterMeta } from 'primevue/datatable'
import { FilterMatchMode, FilterOperator } from '@primevue/core/api';
import { onMounted, ref, watch } from 'vue'

function formatDate(dateStr: string): string {
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

const page = ref<number>(1)

const loading = ref<boolean>(false)

const cases = ref<PagedCaseListingSchema>({
    items: [],
    count: 0,
})

const filters = ref<DataTableFilterMeta>({
    global: { value: null, matchMode: 'contains' },
    case: { value: null, matchMode: 'contains' },
    client_id: { value: null, matchMode: 'contains' },
    tags: { value: null, matchMode: 'contains' },
    location: { value: null, matchMode: 'contains' },
    status: { operator: FilterOperator.OR, constraints: [{ value: null, matchMode: FilterMatchMode.EQUALS }] },
    last_modified_at: { value: null, matchMode: 'dateBefore' },
})

function fetchCases() {
    loading.value = true
    sureApiListCases({ query: { page: page.value, page_size: 2 } }).then((response) => {
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

function onFilterChange(event: any) {
    console.log('Filters changed:', event)
    console.log('Current filters:', filters.value)
}

onMounted(async () => {
    fetchCases()
})

</script>

<template>
    <DataTable lazy :value="cases.items" paginator :rows="2" :total-records="cases.count" @page="onPageChange($event)"
        @filter="onFilterChange($event)" :loading="loading" v-model:filters="filters" filter-display="menu">
        <Column field="case" header="Case">
            <template #body="{ data }">
                {{ data.case }}
            </template>
            <template #filter="{ filterModel }">
                <InputText v-model="filterModel.value" type="text" placeholder="Search by name" />
            </template>
        </Column>
        <Column field="client_id" header="Client">
            <template #body="{ data }">
                {{ data.client_id }}
            </template>
            <template #filter="{ filterModel }">
                <InputText v-model="filterModel.value" type="text" placeholder="Search by client" />
            </template>
        </Column>
        <Column field="tags" header="Tags">
            <template #body="{ data }">
                {{ data.tags.join(', ') }}
            </template>
            <template #filter="{ filterModel }">
                <InputText v-model="filterModel.value" type="text" placeholder="Search by tags" />
            </template>
        </Column>
        <Column field="last_modified_at" header="Last Modified" data-type="date">
            <template #body="{ data }">
                {{ formatDate(data.last_modified_at) }}
            </template>
            <template #filter="{ filterModel }">
                <DatePicker v-model="filterModel.value" :show-icon="true" placeholder="Select date" />
            </template>
        </Column>
        <Column field="location" header="Location">
            <template #body="{ data }">
                {{ data.location }}
            </template>
            <template #filter="{ filterModel }">
                <InputText v-model="filterModel.value" type="text" placeholder="Search by location" />
            </template>
        </Column>
        <Column field="status" header="Status">
            <template #body="{ data }">
                {{ data.status }}
            </template>
            <template #filter="{ filterModel }">
                <InputText v-model="filterModel.value" type="text" placeholder="Search by status" />
            </template>
        </Column>
    </DataTable>
</template>