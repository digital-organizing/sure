<script setup lang="ts">
import { useAccount } from '@/composables/useAccount'
import { useRouter } from 'vue-router'

const { account } = useAccount()
const router = useRouter()
</script>

<template>
  <header>
    <section class="logos">
      <img
        src="/logo.png"
        alt="Logo"
        class="logo"
        @click="router.push({ name: 'consultant-dashboard' })"
      />
      <img
        src="/logo.png"
        alt="Logo"
        class="logo"
        @click="router.push({ name: 'consultant-dashboard' })"
      />
    </section>
    <section class="menu">
      <Button asChild v-slot="slotProps" severity="secondary">
        <RouterLink :to="{ name: 'consultant-dashboard' }" :class="slotProps.class">
          <i class="pi pi-home" />
          Dashboard
        </RouterLink>
      </Button>
      <Button
        as="a"
        :href="'/admin/'"
        v-if="account.is_staff"
        icon="pi pi-cog"
        label="Administration"
        severity="secondary"
      />

      <Button asChild v-slot="slotProps">
        <RouterLink :to="{ name: 'consultant-new-case' }" :class="slotProps.class">
          <i class="pi pi-plus" />
          New Case
        </RouterLink>
      </Button>
      <div class="account">
        <span class="user">{{ account.full_name || account.username }}</span>
        <RouterLink to="/logout" class="signout"
          >Logout
          <i class="pi pi-sign-out"> </i>
        </RouterLink>
      </div>
    </section>
  </header>
</template>

<style scoped>
header {
  display: flex;
  max-width: var(--container-width);
  margin: 0 auto 2rem auto;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
}

.logos {
  display: flex;
  align-items: center;
}

.logo {
  height: 60px;
  cursor: pointer;
}
.menu {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.account {
  display: flex;
  align-items: start;
  justify-content: center;
  flex-direction: column;
}

.account .user {
  font-weight: bold;
}

.signout {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--color-text);
  text-decoration: none;
}
</style>
