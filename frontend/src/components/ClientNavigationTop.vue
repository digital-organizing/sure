<script setup lang="ts">
import { computed, defineEmits, defineProps, ref } from 'vue'
import Menu from 'primevue/menu'
import Button from 'primevue/button'
import IconMenu from './icons/IconMenu.vue'
import type { SectionSchema } from '@/client'

const props = defineProps<{
  sectionTitle: string
  sections: SectionSchema[]
}>()

const emit = defineEmits<{
  (e: 'select-section', index: number): void
}>()

const menu = ref()

const menuItems = computed(() => {
  if (!props.sections?.length) {
    return []
  }

  return [
    {
      label: 'Sections',
      items: props.sections.map((section, index) => ({
        label: section.title,
        command: () => emit('select-section', index),
      })),
    },
  ]
})

function toggle(event: Event) {
  menu.value.toggle(event)
}
</script>

<template>
  <div id="client-navigation-top">
    <div id="section-title-navbar">
      {{ props.sectionTitle }}
    </div>
    <div>
      <Button
        id="menu-button"
        type="button"
        icon="pi pi-ellipsis-v"
        @click="toggle"
        aria-haspopup="true"
        aria-controls="overlay-menu"
      >
        <IconMenu />
      </Button>
      <Menu ref="menu" id="overlay_menu" :model="menuItems" :popup="true" />
    </div>
  </div>
</template>

<style scoped>
#client-navigation-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  align-self: stretch;
}
#menu-button {
  background: transparent;
  border: none;
  box-shadow: none;
  color: var(--color-ahs-black);
  width: 33px;
  height: 33px;
  aspect-ratio: 1/1;
}
#section-title-navbar {
  color: var(--color-ahs-black);
  font-family: 'Circular Std';
  font-size: 24px;
  font-style: normal;
  font-weight: 700;
  line-height: normal;
}
</style>
