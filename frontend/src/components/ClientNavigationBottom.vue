<script setup lang="ts"></script>

<template>
  <div class="client-navigation-bottom">
    <slot></slot>
  </div>
</template>

<style scoped>
.client-navigation-bottom {
  display: flex;
  width: 375px;
  padding: 30px;
  justify-content: space-between;
  align-items: flex-end;

  background: var(--color-ahs-white);
}
</style>
