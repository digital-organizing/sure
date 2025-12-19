<script lang="ts" setup>
import type { LocationSchema } from '@/client'
import { useTexts } from '@/composables/useTexts'
import { formatDate } from '@vueuse/core'
import { computed } from 'vue'

const props = defineProps<{
  location: LocationSchema
}>()

const { getText: t, render: r } = useTexts()

const DAYS = [
  {
    key: 'monday',
    label: computed(() => t('monday').value),
  },
  {
    key: 'tuesday',
    label: computed(() => t('tuesday').value),
  },
  {
    key: 'wednesday',
    label: computed(() => t('wednesday').value),
  },
  {
    key: 'thursday',
    label: computed(() => t('thursday').value),
  },
  {
    key: 'friday',
    label: computed(() => t('friday').value),
  },
  {
    key: 'saturday',
    label: computed(() => t('saturday').value),
  },
  {
    key: 'sunday',
    label: computed(() => t('sunday').value),
  },
]

function formatHours(hours: string[][]) {
  return hours.length > 0 ? hours.map((range) => range.join(' - ')).join(', ') : t('closed').value
}

const isOpen = computed(() => {
  const today = new Date().getDay() // 0 (Sun) to 6 (Sat)
  const index = today === 0 ? 6 : today - 1 // Adjust to 0 (Mon) to 6 (Sun)
  const dayKey = DAYS[index]!.key

  const hours = (
    props.location.opening_hours ? props.location.opening_hours[dayKey] : []
  ) as string[][]

  for (const range of hours) {
    if (range.length != 2) {
      continue
    }
    const [openTime, closeTime] = range
    const currentTime = formatDate(new Date(), 'HH:mm')
    if (currentTime >= openTime! && currentTime <= closeTime!) {
      return true
    }
  }

  return false
})

function onPhoneClick() {
  if (props.location.phone_number) {
    window.open(`tel:${props.location.phone_number}`, '_self')
  }
}
</script>
<template>
  <section>
    <h3>{{ location.name }}</h3>
    <div class="phone-panel">
      <span class="phone">{{ location.phone_number }}</span>
      <Button
        v-if="isOpen && location.phone_number"
        icon="pi pi-phone"
        :label="t('call-now').value"
        severity="success"
        @click="onPhoneClick"
      />
    </div>
    <div>
      <strong>{{ t('address') }}:</strong>
      <div v-html="r(location.address || '')"></div>
    </div>
    <section class="opening-hours">
      <h4>{{ t('opening-hours') }}</h4>
      <ul>
        <li v-for="day in DAYS" :key="day.key">
          <strong>{{ day.label }}:</strong>
          {{ formatHours((location.opening_hours![day.key] as string[][]) || []) }}
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.opening-hours {
  margin-top: 0.5rem;
}

.phone-panel {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.5rem;
}
</style>
