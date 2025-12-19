<script setup lang="ts">
import { useTexts } from '@/composables/useTexts'

const { getText: t, render: r } = useTexts()
</script>
<template>
  <main>
    <h1>{{ t('imprint') }}</h1>
    <section>
      <p class="lead">
        {{ t('imprint-lead') }}
      </p>
      <p>
        {{ t('imprint-text') }}
      </p>
      <p :v-html="r('imprint-contact')"></p>
    </section>
  </main>
</template>
<style scoped>
p {
  margin-bottom: 1rem;
}
p.lead {
  font-size: 1rem;
  font-weight: bold;
}
main {
  padding: 2rem;
  margin: auto;
  max-width: 600px;
}
</style>
