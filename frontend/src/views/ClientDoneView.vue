<script setup lang="ts">
defineProps<{
  caseId: string
}>()
</script>
<template>
  <main>
    <h3>Thank you! Your information has been submitted successfully.</h3>
    <p>
      Your case ID is {{ caseId }}, please save it for your records, together with the secret
      password you created earlier.
    </p>
    <p>You can close this window now.</p>
    <p>The test results will be available under this link:</p>
  </main>
</template>

<style scoped>
main {
  max-width: 600px;
  margin: auto;
  padding: 2rem;
}
</style>
