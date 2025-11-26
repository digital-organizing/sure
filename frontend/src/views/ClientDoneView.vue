<script setup lang="ts">
import ClientLogoHeader from '@/components/ClientLogoHeader.vue';

const props = defineProps<{
  caseId: string
}>()
</script>

<template>
  <div class="client-form-view">
    <div>
      <ClientLogoHeader :case-id="props.caseId"/>
    </div>
    <div class="client-section-element" id="client-done-flex">
      <h1 class="client-h1" style="margin: 0;">
          Thank You
      </h1>
      <p class="client-body" style="margin: 0;">
        Lorem ipsum dolor sit amet consectetur adipisicing elit. Cupiditate fugiat facere ipsum modi ipsam repudiandae, quam quia officia est! Dignissimos eaque quaerat excepturi optio harum porro veritatis autem id corrupti.
      </p>
      <p class="client-body" style="margin: 0;">
        Bitte notieren sie sich ihre ID-Nummer:
      </p>
      <p id="client-done-caseid" style="margin: 0;">
        {{ props.caseId }}
      </p>

    </div>

  </div>
</template>

<style scoped>
#client-done-flex {
    display: flex;
    padding-top: 30px;
    padding-bottom: 30px;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 20px;
    margin-top: 75px;
}

#client-done-caseid {
text-align: center;
font-size: 28px;
font-style: normal;
font-weight: 700;
line-height: 24.5px;
}

</style>
