<script setup lang="ts">
import { tenantsApiGetTenant, type TenantSchema } from '@/client'
import { useAccount } from '@/composables/useAccount'
import { useTexts } from '@/composables/useTexts'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const { account } = useAccount()
const router = useRouter()

const tenant = ref<TenantSchema | null>(null)

const { getText: t, setLanguage, getAvailableLanguages, language, render: r } = useTexts()

const langs = ref<[string, string][]>([])

onMounted(() => {
  tenantsApiGetTenant().then((response) => {
    if (response.data) tenant.value = response.data
  })

  getAvailableLanguages().then((l) => {
    langs.value = l
  })
})

const drawerVisible = ref(false)
</script>

<template>
  <header>
    <section class="logos">
      <img
        v-if="tenant?.logo"
        :src="tenant.logo"
        :alt="tenant.name"
        class="logo"
        @click="router.push({ name: 'consultant-dashboard' })"
      />
      <img
        src="/logo.png"
        :alt="t('Logo').value"
        class="logo"
        @click="router.push({ name: 'consultant-dashboard' })"
      />
    </section>
    <section class="menu">
      <Button asChild v-slot="slotProps" severity="secondary">
        <RouterLink :to="{ name: 'consultant-dashboard' }" :class="slotProps.class">
          <i class="pi pi-home" />
          {{ t('dashboard') }}
        </RouterLink>
      </Button>
      <Button
        as="a"
        :href="'/admin/'"
        v-if="account.is_staff"
        icon="pi pi-cog"
        :label="t('administration').value"
        severity="secondary"
      />

      <Button asChild v-slot="slotProps">
        <RouterLink :to="{ name: 'consultant-new-case' }" :class="slotProps.class">
          <i class="pi pi-plus" />
          {{ t('new-case') }}
        </RouterLink>
      </Button>
      <div class="account">
        <span class="user">{{ account.full_name || account.username }}</span>
        <RouterLink to="/logout" class="signout"
          >{{ t('logout') }}
          <i class="pi pi-sign-out"> </i>
        </RouterLink>
      </div>
      <Button
        icon="pi pi-bars"
        severity="secondary"
        @click="drawerVisible = true"
        aria-label="Open Menu"
        variant="text"
      />
    </section>
  </header>

  <Drawer header="Menu" v-model:visible="drawerVisible" position="right">
    <section class="navigation">
      <div class="text languages">
        <span
          v-for="lang in langs"
          :key="lang[0]"
          class="lang"
          :class="{ active: lang[0] == language }"
          @click="setLanguage(lang[0]).then(() => (drawerVisible = false))"
          >{{ lang[0].toUpperCase() }}</span
        >
      </div>
      <i class="pi pi-book icon" />
      <a :href="t('manual-link').value" target="_blank" rel="noopener noreferrer" class="text">
        {{ t('user-manual') }}
      </a>
      <i class="pi pi-phone icon" />
      <div class="text support-contact" v-html="r('support-contact')"></div>
    </section>
  </Drawer>
</template>

<style scoped>
header {
  display: flex;
  max-width: var(--container-width);
  margin: 0 auto 2rem auto;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  overflow-x: auto;
}

.navigation {
  display: grid;
  grid-template-columns: 2rem auto;
  gap: 1rem 0.5rem;
}

.text {
  grid-column: 2 / span 1;
}

.support-contact {
  grid-column: 2 / span 1;
}

.icon {
  grid-column: 1 / span 1;
}

.languages {
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
  gap: 0.5rem;
}

a.text {
  text-decoration: none;
  color: var(--text-color);
}

.lang {
  cursor: pointer;
}
.lang.active {
  font-weight: bold;
  text-decoration: underline;
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
