<script setup lang="ts">
import { tenantsApiGetTenantById, type TenantSchema } from '@/client'
import { onMounted, ref } from 'vue'

const props = defineProps<{
  caseId: string
}>()

const tenant = ref<TenantSchema | null>(null)

onMounted(() => {
  tenantsApiGetTenantById({ path: { case_id: props.caseId } }).then((response) => {
    if (response.data) tenant.value = response.data
  })
})
</script>

<template>
  <div id="client-welcome-logo-header">
    <img v-if="tenant?.logo" :src="tenant.logo" :alt="tenant.name" class="logo" />
    <img src="/logo.png" class="logo" />
  </div>
</template>

<style scoped>
#client-welcome-logo-header {
  display: flex;
  width: 100%;
  padding: 50px 20px 30px 20px;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.logo {
  height: 60px;
}
</style>
