<script lang="ts" setup>
import type { FreeFormTestSchema } from '@/client'
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'

const md = new MarkdownIt({
  linkify: true,
  html: true,
  breaks: true,
  typographer: true,
})
const props = defineProps<{
  result: FreeFormTestSchema
}>()

function render(text: string): string {
  return md.renderInline(text)
}
const label = computed(() => {
  return render(`**${props.result.name}**: ${props.result.result || ''}`)
})
</script>

<template>
  <section :style="{ '--result-color': '#aaa' }">
    <p v-html="label"></p>
  </section>
</template>

<style scoped>
section {
  background-color: var(--result-color);
  border-radius: 10px;
  padding: 20px;
  margin-top: 5px;
  margin-bottom: 5px;
}

p {
  margin: 0;
  line-height: 1.5;
}
</style>
