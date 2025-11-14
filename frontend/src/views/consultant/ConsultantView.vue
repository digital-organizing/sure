<template>
  <header>Here comes the header content
    <Button asChild v-slot="slotProps">
      <RouterLink :to="{name: 'consultant-new-case'}" :class="slotProps.class">Hallo</RouterLink>
    </Button> 

  </header>
  <main>
    <router-view />
  </main>
</template>
