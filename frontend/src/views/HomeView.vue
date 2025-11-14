<script setup lang="ts">
import { coreApiAccount, type AccountResponse } from '@/client';
import { useUrlSearchParams } from '@vueuse/core';
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router';

const params = useUrlSearchParams();
const router = useRouter();
const user = ref<AccountResponse|null>(null);

onMounted(async () => {
  if (params.case) {
    router.replace({name: 'client-form', params: {caseId: params.case}}) 
    return;
  }
  
  const response = await coreApiAccount();
  
  if (!response.data) {
    router.replace({ name: 'login' });
    return;
  }
  user.value = response.data;
  
  if (!response.data.username) {
    router.replace({ name: 'login' });
    return;
  }
  
  if(!response.data.is_staff) {
    router.replace({ name: 'consultant-dashboard' });
    return;
  }

})
</script>

<template>
  <h1>You did it!</h1>
  <p>Hello World!</p>
  <RouterLink :to="{name: 'consultant-dashboard'}">Go to Dashboard</RouterLink>

  <RouterLink to="/admin/" v-if="user?.is_staff">Go to Admin</RouterLink>
</template>
