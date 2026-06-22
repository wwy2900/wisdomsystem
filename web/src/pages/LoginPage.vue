<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();
const router = useRouter();
const form = reactive({
  username: "demo_user",
  password: "User12345!",
});
const loading = ref(false);

async function submit() {
  loading.value = true;
  try {
    const user = await authStore.login(form.username, form.password);
    router.push(user.role === "admin" ? "/admin/knowledge" : "/chat");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="login-page">
    <div class="login-panel">
      <p class="hero-kicker">Browser Frontend</p>
      <h1 data-testid="login-title">智扫通 Vue3 前端</h1>
      <p class="hero-copy">
        使用 FastAPI 的会话 Cookie 登录，区分普通用户与管理员工作流。默认引导账号可在后端
        `AUTH_BOOTSTRAP_*` 环境变量中替换。
      </p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" show-password type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-button class="login-button" :loading="loading" type="primary" @click="submit">登录</el-button>
      </el-form>
    </div>
  </section>
</template>
