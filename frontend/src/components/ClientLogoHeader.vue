<script setup lang="ts">

const props = defineProps<{
    logo: string
}>()

</script>

<template>
    <div id="client-welcome-logo-header">
        <img src="../../public/logo.png"/>
    </div>
</template>

<style scoped>
#client-welcome-logo-header {
  display: flex;
  width: 375px;
  padding: 50px 20px 30px 20px;
  align-items: center;
  gap: 5px;
}
</style>