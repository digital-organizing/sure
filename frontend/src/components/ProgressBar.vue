<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
  total: Number,
  value: Number,
})

const steps = computed(() => {
  return [...Array(props.total?.valueOf() || 0).keys()].map(i => {
    return {
      first: i === 0,
      last: i === (props.total?.valueOf() || 1) - 1,
      index: i + 1,
      completed: props.value !== undefined && i < props.value.valueOf(),
    }
  })
})

</script>

<template>
  <div id="progress-bar">
    <template v-for="step in steps" :key="step.index">
      <div class="pre" :class="{'completed': step.completed}" v-if="!step.first"></div>
      <div class="circle" :class="{'completed': step.completed}"></div>
      <div class="post" :class="{'completed': step.completed}" v-if="!step.last"></div>
    </template>
  </div>
</template>

<style scoped>
#progress-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  --current-color: #bcbcbc;
}
.step {
  display: flex;
  align-items: center;
}
.circle {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background-color: var(--current-color);
  z-index: 1;
}
    
.completed {
  --current-color: black;
}
    
.pre, .post {
  flex: 1;
  height: 4px;
  background-color: var(--current-color);
}
</style>
