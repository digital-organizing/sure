<script setup lang="ts">
import { useBanner } from '@/composables/useBanner'
import { useRender } from '@/composables/useRender'

const { showBanners, dismissBanner } = useBanner()
const { renderMarkdown } = useRender()
</script>

<template>
  <main>
    <header>
      <Message
        :severity="banner.severity"
        variant="outlined"
        closable
        v-for="banner in showBanners"
        :key="banner.id!"
        @close="dismissBanner(banner.id!)"
      >
        <div v-html="renderMarkdown(banner.content)" />
      </Message>
    </header>
    <router-view />
  </main>
</template>

<style scoped>
main {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  gap: 1rem;
}
header {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
</style>
