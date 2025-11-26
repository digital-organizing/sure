<script setup lang="ts">
import { coreApiAccount, type AccountResponse } from '@/client'
import { useUrlSearchParams } from '@vueuse/core'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const params = useUrlSearchParams()
const router = useRouter()
const user = ref<AccountResponse | null>(null)
const loading = ref(true)

onMounted(async () => {
  if (params.case) {
    router.replace({ name: 'client-start', params: { caseId: params.case } })
    return
  }

  const response = await coreApiAccount()

  if (!response.data?.verified) {
    router.replace({ name: 'login' })
    return
  }
  user.value = response.data

  if (!response.data.username) {
    router.replace({ name: 'login' })
    return
  }

  router.replace({ name: 'consultant-dashboard' })
  loading.value = false
})
</script>

<template>
  <section v-if="!loading">
    <RouterLink :to="{ name: 'consultant-dashboard' }">Go to Dashboard</RouterLink>

    <a href="/admin/" v-if="user?.is_staff">Go to Admin</a>
  </section>
</template>
