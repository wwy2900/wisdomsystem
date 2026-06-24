<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { describeRequestError } from "@/api/http";
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();
const router = useRouter();

const activeTab = ref<"login" | "register">("login");
const loading = ref(false);

const loginForm = reactive({
  username: "demo_user",
  password: "User12345!",
});

const registerForm = reactive({
  username: "",
  display_name: "",
  password: "",
  confirmPassword: "",
});

function resetRegisterForm() {
  registerForm.username = "";
  registerForm.display_name = "";
  registerForm.password = "";
  registerForm.confirmPassword = "";
}

async function submitLogin() {
  loading.value = true;
  try {
    const user = await authStore.login(loginForm.username, loginForm.password);
    router.push(user.role === "admin" ? "/admin/knowledge" : "/chat");
  } catch (error) {
    ElMessage.error(describeRequestError(error));
  } finally {
    loading.value = false;
  }
}

async function submitRegister() {
  if (registerForm.password !== registerForm.confirmPassword) {
    ElMessage.error("Passwords do not match.");
    return;
  }

  loading.value = true;
  try {
    await authStore.register({
      username: registerForm.username,
      display_name: registerForm.display_name,
      password: registerForm.password,
    });
    resetRegisterForm();
    router.push("/chat");
  } catch (error) {
    ElMessage.error(describeRequestError(error));
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="login-page">
    <div class="login-panel">
      <p class="hero-kicker">Browser Frontend</p>
      <h1 data-testid="login-title">WisdomSystem Workspace</h1>
      <p class="hero-copy">
        Sign in with an existing account or register a new user account. Admin accounts remain restricted to admin
        creation and bootstrap setup.
      </p>

      <el-tabs v-model="activeTab" stretch>
        <el-tab-pane label="Login" name="login">
          <el-form label-position="top" @submit.prevent="submitLogin">
            <el-form-item label="Username">
              <el-input v-model="loginForm.username" autocomplete="username" placeholder="Enter your username" />
            </el-form-item>
            <el-form-item label="Password">
              <el-input
                v-model="loginForm.password"
                autocomplete="current-password"
                placeholder="Enter your password"
                show-password
                type="password"
              />
            </el-form-item>
            <el-button class="login-button" :loading="loading" type="primary" @click="submitLogin">Login</el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="Register" name="register">
          <el-form label-position="top" @submit.prevent="submitRegister">
            <el-form-item label="Username">
              <el-input v-model="registerForm.username" autocomplete="username" placeholder="Choose a username" />
            </el-form-item>
            <el-form-item label="Display name">
              <el-input
                v-model="registerForm.display_name"
                autocomplete="name"
                placeholder="Enter the name shown in the app"
              />
            </el-form-item>
            <el-form-item label="Password">
              <el-input
                v-model="registerForm.password"
                autocomplete="new-password"
                placeholder="At least 8 characters"
                show-password
                type="password"
              />
            </el-form-item>
            <el-form-item label="Confirm password">
              <el-input
                v-model="registerForm.confirmPassword"
                autocomplete="new-password"
                placeholder="Re-enter your password"
                show-password
                type="password"
              />
            </el-form-item>
            <el-button class="login-button" :loading="loading" type="primary" @click="submitRegister">
              Create account
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </section>
</template>
