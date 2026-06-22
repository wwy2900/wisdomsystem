import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import AdminKnowledgePage from "@/pages/AdminKnowledgePage.vue";
import ChatPage from "@/pages/ChatPage.vue";
import ForbiddenPage from "@/pages/ForbiddenPage.vue";
import LoginPage from "@/pages/LoginPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginPage,
      meta: { guestOnly: true },
    },
    {
      path: "/chat",
      name: "chat",
      component: ChatPage,
      meta: { requiresAuth: true },
    },
    {
      path: "/admin/knowledge",
      name: "admin-knowledge",
      component: AdminKnowledgePage,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: "/403",
      name: "forbidden",
      component: ForbiddenPage,
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/chat",
    },
  ],
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore();
  if (!authStore.user && !authStore.restoring) {
    await authStore.restoreSession();
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { path: "/login" };
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return { path: "/chat" };
  }

  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return { path: "/403" };
  }

  return true;
});

export default router;
