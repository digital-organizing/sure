import {
  laborApiCancelOrder,
  laborApiGenerateOrder,
  laborApiGetLaboratory,
  laborApiListLabOrders,
  type LaboratorySchema,
  type LabOrderSchema,
  type PatientDataSchema,
} from '@/client'
import { ref } from 'vue'
import { useCase } from './useCase'
import { createGlobalState } from '@vueuse/core'

export const useLab = createGlobalState(() => {
  const { onCaseId } = useCase()

  const labOrders = ref<LabOrderSchema[]>([])
  const error = ref<string | null>(null)
  const labInfo = ref<LaboratorySchema | null>(null)

  async function fetchLabInfo(caseId: string) {
    laborApiGetLaboratory({ path: { case_id: caseId } }).then((response) => {
      if (response.data) {
        labInfo.value = response.data
      } else if (response.error) {
        error.value =
          (response.error as { detail?: string }).detail ||
          'An error occurred while fetching lab information.'
      }
    })
  }

  async function fetchLabOrders(caseId: string) {
    laborApiListLabOrders({ path: { case_id: caseId } }).then((response) => {
      if (response.data) {
        labOrders.value = response.data
      } else if (response.error) {
        error.value =
          (response.error as { detail?: string }).detail ||
          'An error occurred while fetching lab orders.'
      }
    })
  }

  async function submitLabOrder(caseId: string, patientData: PatientDataSchema) {
    return laborApiGenerateOrder({ body: patientData, path: { case_id: caseId } }).then(
      (response) => {
        if (response.data) {
          labOrders.value = [response.data].concat(labOrders.value)
          return response.data
        }
      },
    )
  }

  async function cancelLabOrder(caseId: string, orderId: string) {
    laborApiCancelOrder({ path: { case_id: caseId, order_number: orderId } }).then((response) => {
      if (response.data) {
        labOrders.value = response.data
        return response.data
      }
    })
  }

  onCaseId((caseId: string | null) => {
    if (!caseId) return
    fetchLabInfo(caseId)
    fetchLabOrders(caseId)
  })

  return {
    labOrders,
    submitLabOrder,
    labInfo,
    fetchLabInfo,

    error,
    cancelLabOrder,
  }
})
