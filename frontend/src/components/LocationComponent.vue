<script lang="ts" setup>
import type { LocationSchema } from '@/client';

    
const props = defineProps<{
    location: LocationSchema
}>();

function formatHours(hours: string[][])
{
    return hours.length > 0 ? hours.map(range => range.join(' - ')).join(', ') : 'Closed';
}

</script>
<template>
    <section>
    <h3>{{ location.name }}</h3>
    <p>Phone Number: <a href="tel:{{ location.phone_number }}">{{ location.phone_number }}</a></p>
    <section class="opening-hours">
        <h4>Opening Hours</h4>
        <ul>
            <li v-for="(hours, day) in location.opening_hours" :key="day">
                <strong>{{ day }}:</strong> {{ formatHours(hours as string[][]) }}
            </li>
        </ul>
    </section>
    </section> 
</template>
