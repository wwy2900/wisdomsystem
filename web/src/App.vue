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
          <div class="brand-title">智能客服工作台</div>
        </div>
        <nav class="main-nav">
          <RouterLink class="nav-link" to="/chat">聊天工作台</RouterLink>
          <RouterLink v-if="authStore.isAdmin" class="nav-link" to="/admin/knowledge">知识库管理</RouterLink>
        </nav>
        <div class="account-block" v-if="authStore.user">
          <div class="account-meta">
            <span>{{ authStore.user.display_name }}</span>
            <small>{{ authStore.user.role }}</small>
          </div>
          <button class="ghost-button" type="button" @click="handleLogout">退出</button>
        </div>
      </header>
      <main class="page-shell">
        <RouterView />
      </main>
    </template>
    <RouterView v-else />
  </div>
</template>
