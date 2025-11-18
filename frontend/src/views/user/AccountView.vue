<template>
  <main>
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
  justify-content: center;
  height: 80vh;
}

.account-panel {
  max-width: 520px;
  width: 100%;
}
</style>
