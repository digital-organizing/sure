<script setup lang="ts"></script>

<template>
  <main>
    <div class="logo">
      <img src="/sure_logo_C.png" />
    </div>
    <Panel header="SURE" class="account-panel">
      <router-view></router-view>
    </Panel>
  </main>
</template>

<style scoped>
main {
  margin: 0 auto;
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: flex-start;
  height: 80vh;
  gap: 1rem;
}

.account-panel {
  max-width: 520px;
  width: 100%;
}
.logo {
  display: flex;
  width: 100%;
  padding: 20px 0px 0px 0px;
  align-items: center;
  justify-content: center;
}
.logo img {
  height: 120px;
}
</style>
