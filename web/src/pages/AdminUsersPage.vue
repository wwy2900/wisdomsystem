<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import * as usersApi from "@/api/users";
import type { UserRole, UserSummary } from "@/types";

const loading = ref(false);
const saving = ref(false);
const users = ref<UserSummary[]>([]);

const createForm = reactive({
  username: "",
  display_name: "",
  password: "",
  confirmPassword: "",
  role: "user" as UserRole,
});

function resetCreateForm() {
  createForm.username = "";
  createForm.display_name = "";
  createForm.password = "";
  createForm.confirmPassword = "";
  createForm.role = "user";
}

async function loadUsers() {
  loading.value = true;
  try {
    const response = await usersApi.listUsers();
    users.value = response.users;
  } finally {
    loading.value = false;
  }
}

async function submitCreateUser() {
  if (saving.value) {
    return;
  }

  if (createForm.password !== createForm.confirmPassword) {
    ElMessage.error("Passwords do not match.");
    return;
  }

  saving.value = true;
  try {
    await usersApi.createUser({
      username: createForm.username,
      display_name: createForm.display_name,
      password: createForm.password,
      role: createForm.role,
    });
    ElMessage.success("User created.");
    resetCreateForm();
    await loadUsers();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "User creation failed.");
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadUsers().catch((error) => {
    ElMessage.error(error instanceof Error ? error.message : "User page initialization failed.");
  });
});
</script>

<template>
  <section class="admin-layout">
    <div class="admin-grid">
      <article class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Create</p>
            <h2>Create User</h2>
          </div>
        </div>

        <el-form label-position="top" @submit.prevent="submitCreateUser">
          <el-form-item label="Username">
            <el-input v-model="createForm.username" placeholder="Choose a unique username" />
          </el-form-item>
          <el-form-item label="Display name">
            <el-input v-model="createForm.display_name" placeholder="Displayed name in the app" />
          </el-form-item>
          <el-form-item label="Role">
            <el-select v-model="createForm.role" placeholder="Select a role">
              <el-option label="User" value="user" />
              <el-option label="Admin" value="admin" />
            </el-select>
          </el-form-item>
          <el-form-item label="Password">
            <el-input v-model="createForm.password" placeholder="At least 8 characters" show-password type="password" />
          </el-form-item>
          <el-form-item label="Confirm password">
            <el-input
              v-model="createForm.confirmPassword"
              placeholder="Re-enter the password"
              show-password
              type="password"
            />
          </el-form-item>
          <el-button :loading="saving" type="primary" @click="submitCreateUser">Create User</el-button>
        </el-form>
      </article>

      <article class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Overview</p>
            <h2>Account List</h2>
          </div>
        </div>

        <el-table :data="users" stripe v-loading="loading">
          <el-table-column label="Username" prop="username" min-width="160" />
          <el-table-column label="Display name" prop="display_name" min-width="180" />
          <el-table-column label="Role" prop="role" width="120" />
          <el-table-column label="Status" width="120">
            <template #default="{ row }">
              {{ row.is_active ? "active" : "inactive" }}
            </template>
          </el-table-column>
          <el-table-column label="Created at" prop="created_at" min-width="220" />
        </el-table>
      </article>
    </div>
  </section>
</template>
