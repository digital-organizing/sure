<script lang="ts" setup>
import type { TestResultOptionSchema, TestResultSchema, TestSchema } from '@/client'
import chroma from 'chroma-js'
import { useRender } from '@/composables/useRender'

const props = defineProps<{
  resultOption: TestResultOptionSchema
  result: TestResultSchema
  test: TestSchema
  infoText?: string | undefined | null
}>()

const { renderMarkdown: render } = useRender()

function formatInformationText(text: string): string {
  if (props.test.test_kind.interpretation_needed) {
    if (text == '') {
      return `${props.test.test_kind.name}: **${props.resultOption.label}**\n${props.test.test_kind.note}: ${props.result.note || 'N/A'}`
    }
    return text.replace('XXX', props.result.note || 'N/A')
  }
  if (text === '') {
    return `${props.test.test_kind.name}: **${props.resultOption.label}**`
  }
  return text
}

function getBackgroundColor(color: string): string {
  const scale = chroma.scale(['#ffffff', color]).mode('lab').colors(10)
  if (!scale[4]) {
    return '#aaa'
  }
  return scale[4]
}
</script>

<template>
  <section :style="{ '--result-color': getBackgroundColor(props.resultOption.color || '#aaa') }">
    <p v-html="render(formatInformationText(resultOption.information_text ?? ''))"></p>
    <p v-if="infoText" v-html="render(infoText)"></p>
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
