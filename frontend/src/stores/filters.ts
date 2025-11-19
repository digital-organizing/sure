import { defineStore } from 'pinia'
import type { DataTableFilterMeta } from 'primevue'
import { ref } from 'vue'

import { FilterMatchMode, FilterOperator } from '@primevue/core/api'

export const useFilterStore = defineStore('filters', () => {
  const filters = ref<DataTableFilterMeta>({
    search: { value: null, matchMode: 'contains' },
    case: { value: null, matchMode: 'contains' },
    client_id: { value: null, matchMode: 'contains' },
    external_id: { value: null, matchMode: 'contains' },
    tags: {
      operator: FilterOperator.OR,
      constraints: [{ value: null, matchMode: FilterMatchMode.CONTAINS }],
    },
    location: { value: null, matchMode: 'equals' },
    status: { value: null, matchMode: 'in' },
    last_modified_at: {
      operator: FilterOperator.AND,
      constraints: [{ value: null, matchMode: FilterMatchMode.DATE_AFTER }],
    },
  })
  return {
    filters,
  }
})
