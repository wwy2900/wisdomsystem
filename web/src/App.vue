<script setup lang="ts">
import { computed } from "vue";
import { useRouter, useRoute } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const showShell = computed(() => route.path !== "/login");

async function handleLogout() {
  await authStore.logout();
  router.push("/login");
}
</script>

<template>
  <div class="app-root">
    <template v-if="showShell">
      <header class="topbar">
        <div class="brand-block">
          <div class="brand-kicker">WisdomSystem</div>
          <div class="brand-title">Customer Service Workspace</div>
        </div>
        <nav class="main-nav">
          <RouterLink class="nav-link" to="/chat">Chat</RouterLink>
          <RouterLink v-if="authStore.isAdmin" class="nav-link" to="/admin/knowledge">Knowledge</RouterLink>
          <RouterLink v-if="authStore.isAdmin" class="nav-link" to="/admin/users">Users</RouterLink>
        </nav>
        <div class="account-block" v-if="authStore.user">
          <div class="account-meta">
            <span>{{ authStore.user.display_name }}</span>
            <small>{{ authStore.user.role }}</small>
          </div>
          <button class="ghost-button" type="button" @click="handleLogout">Logout</button>
        </div>
      </header>
      <main class="page-shell">
        <RouterView />
      </main>
    </template>
    <RouterView v-else />
  </div>
</template>
