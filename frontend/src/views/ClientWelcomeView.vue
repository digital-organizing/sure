<script setup lang="ts">
import IconRightArrow from '@/components/icons/IconRightArrow.vue'
import IconClock from '@/components/icons/IconClock.vue'
import ClientLogoHeader from '@/components/ClientLogoHeader.vue';
import router from '@/router';


const props = defineProps<{
    caseId: string
}>()


function onStart() {
    router.push(`/client/${props.caseId}/form`)
}

</script>

<template>
    <div class="client-form-view">
        <div id="client-logo-header">
            <ClientLogoHeader />
        </div>
        <div class="client-section-element">
            <div id="client-welcome-flex">
                <h1 class="client-h1">
                    Guten Tag,
                </h1>
                <p class="client-body">
                    Lorem ipsum dolor sit, amet consectetur adipisicing elit. Atque molestiae minus vitae eos eveniet quas consectetur non vel, qui molestias corrupti inventore eaque necessitatibus debitis exercitationem odio minima iste. Possimus.
                </p>
                <Button class="button-extra-large" severity="primary" size="large" icon="pi pi-right-arrow" label="Start" rounded @click="onStart">Start <IconRightArrow/></Button>
            </div>
        </div>
        <div id="client-welcome-time-wrapper">
            <div id="client-welcome-time">
                <IconClock id="clock-icon"/>
                <div>
                    <p id="client-welcome-time-body">
                        Das Ausfüllen des Fragebogens nimmt ca. 15min in Anspruch.
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>


<style scoped>
#client-welcome-flex {
    display: flex;
    padding-top: 30px;
    padding-bottom: 30px;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 20px;
}

#client-welcome-time {
    display: flex;
    width: 375px;
    height: 100px;
    padding: 30px 50px;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
    flex-direction: row;
}

#clock-icon {
    width: 40px;
    height: 40px;
    aspect-ratio: 1/1;
    flex-shrink: 0;
}

#client-welcome-time-body {
    color: var(--color-ahs-black);
    font-size: 15px;
    font-style: normal;
    font-weight: 450;
    line-height: 20px;
}

#client-welcome-time-wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
}
</style>
