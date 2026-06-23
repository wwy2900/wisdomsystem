import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("@/pages/LoginPage.vue"),
      meta: { guestOnly: true },
    },
    {
      path: "/chat",
      name: "chat",
      component: () => import("@/pages/ChatPage.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/admin/knowledge",
      name: "admin-knowledge",
      component: () => import("@/pages/AdminKnowledgePage.vue"),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: "/admin/users",
      name: "admin-users",
      component: () => import("@/pages/AdminUsersPage.vue"),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: "/403",
      name: "forbidden",
      component: () => import("@/pages/ForbiddenPage.vue"),
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
