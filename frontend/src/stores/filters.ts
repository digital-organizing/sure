import { defineStore } from 'pinia'
import type { DataTableFilterMeta } from 'primevue'
import { ref } from 'vue'

import { FilterMatchMode, FilterOperator } from '@primevue/core/api'

export const useFilterStore = defineStore('filters', () => {
  const filters = ref<DataTableFilterMeta>({
    search: { value: null, matchMode: FilterMatchMode.CONTAINS },
    case: { value: null, matchMode: FilterMatchMode.CONTAINS },
    client_id: { value: null, matchMode: FilterMatchMode.CONTAINS },
    external_id: { value: null, matchMode: FilterMatchMode.CONTAINS },
    tags: {
      operator: FilterOperator.OR,
      constraints: [{ value: null, matchMode: FilterMatchMode.CONTAINS }],
    },
    location: { value: null, matchMode: FilterMatchMode.IN },
    status: { value: null, matchMode: FilterMatchMode.IN },
    last_modified_at: {
      operator: FilterOperator.AND,
      constraints: [{ value: null, matchMode: FilterMatchMode.DATE_AFTER }],
    },
    created_at: {
      operator: FilterOperator.AND,
      constraints: [{ value: null, matchMode: FilterMatchMode.DATE_AFTER }],
    },
  })
  return {
    filters,
  }
})
