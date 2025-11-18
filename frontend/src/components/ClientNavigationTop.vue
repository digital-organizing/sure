<script setup lang="ts">
import { defineProps, ref } from 'vue'
import Menu from 'primevue/menu';
import Button from 'primevue/button';
import IconMenu from './icons/IconMenu.vue';


const props = defineProps<{
    sectionTitle: string
}>()

const menu = ref();


function toggle(event: Event) {
    menu.value.toggle(event);
}

</script>



<template>
    <div id="client-navigation-top">
        <div id="section-title-navbar">
            {{ props.sectionTitle }}
        </div>
        <div>
            <Button id="menu-button" type="button" icon="pi pi-ellipsis-v" @click="toggle" aria-haspopup="true" aria-controls="overlay-menu"> <IconMenu/> </Button>
            <Menu ref="menu" id="overlay_menu" :popup="true" />
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
    font-family: "Circular Std";
    font-size: 24px;
    font-style: normal;
    font-weight: 700;
    line-height: normal;
}
</style>
