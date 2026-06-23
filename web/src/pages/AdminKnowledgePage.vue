<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { useKnowledgeStore } from "@/stores/knowledge";

const SUPPORTED_FILE_TYPES = "txt, pdf, docx, xlsx, csv, md, json";

const knowledgeStore = useKnowledgeStore();

const uploadFile = ref<File | null>(null);
const uploadKey = ref(0);
const uploadingAdminFile = ref(false);
const searchText = ref("");
const searchK = ref(5);
const filterUserId = ref(knowledgeStore.adminFilterUserId);
const deleteDocId = ref("");
const rebuildConfirmed = ref(false);

const hasSelectedFile = computed(() => Boolean(uploadFile.value));
const selectedFileName = computed(() => uploadFile.value?.name ?? "");
const selectedFileSize = computed(() => (uploadFile.value ? formatFileSize(uploadFile.value.size) : ""));
const pageStart = computed(() => {
  if (knowledgeStore.adminTotal === 0 || knowledgeStore.adminChunks.length === 0) {
    return 0;
  }
  return (knowledgeStore.adminCurrentPage - 1) * knowledgeStore.adminPageSize + 1;
});
const pageEnd = computed(() => {
  if (pageStart.value === 0) {
    return 0;
  }
  return Math.min(pageStart.value + knowledgeStore.adminChunks.length - 1, knowledgeStore.adminTotal);
});

function formatFileSize(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function resetUploadFile() {
  uploadFile.value = null;
  uploadKey.value += 1;
}

function handleUploadFile(event: Event) {
  const target = event.target as HTMLInputElement;
  uploadFile.value = target.files?.[0] ?? null;
}

async function refreshList() {
  await knowledgeStore.refreshAdminChunks({ userId: filterUserId.value });
}

async function applyFilter() {
  await knowledgeStore.refreshAdminChunks({
    page: 1,
    userId: filterUserId.value,
  });
}

async function handlePageChange(page: number) {
  await knowledgeStore.refreshAdminChunks({ page, userId: filterUserId.value });
}

async function handlePageSizeChange(pageSize: number) {
  await knowledgeStore.refreshAdminChunks({
    page: 1,
    pageSize,
    userId: filterUserId.value,
  });
}

async function submitUpload() {
  if (!uploadFile.value || uploadingAdminFile.value) {
    return;
  }

  uploadingAdminFile.value = true;

  try {
    const result = await knowledgeStore.uploadAdminFile(uploadFile.value);
    ElMessage.success(
      result.skipped
        ? `Upload skipped: ${result.reason || "duplicate or unsupported file"}`
        : `Shared knowledge updated with ${result.chunk_count} chunk(s).`,
    );
    resetUploadFile();
    await refreshList();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Shared upload failed.");
  } finally {
    uploadingAdminFile.value = false;
  }
}

async function searchKnowledge() {
  if (!searchText.value.trim()) {
    ElMessage.warning("Enter a search query first.");
    return;
  }

  try {
    await knowledgeStore.searchAdmin(searchText.value, searchK.value, filterUserId.value || undefined);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Search failed.");
  }
}

async function deleteChunk(docId?: string) {
  const targetDocId = (docId || deleteDocId.value).trim();
  if (!targetDocId) {
    ElMessage.warning("Enter a doc_id before deleting.");
    return;
  }

  try {
    const result = await knowledgeStore.deleteAdminChunk(targetDocId, filterUserId.value || undefined);
    ElMessage.success(result.deleted ? `Deleted ${targetDocId}.` : `${targetDocId} was not found.`);
    deleteDocId.value = "";
    await refreshList();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Delete failed.");
  }
}

async function rebuildKnowledgeBase() {
  if (!rebuildConfirmed.value) {
    ElMessage.warning("Confirm the rebuild before running it.");
    return;
  }

  try {
    const result = await knowledgeStore.rebuild();
    ElMessage.success(
      `Rebuild complete: ${result.file_count} file(s), ${result.chunk_count} chunk(s), ${result.skipped_count} skipped.`,
    );
    await refreshList();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Rebuild failed.");
  }
}

watch(filterUserId, () => {
  knowledgeStore.setAdminPage(1);
});

onMounted(() => {
  refreshList().catch((error) => {
    ElMessage.error(error instanceof Error ? error.message : "Page initialization failed.");
  });
});
</script>

<template>
  <section class="admin-layout">
    <div class="admin-grid">
      <article class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Upload</p>
            <h2>Shared Knowledge Upload</h2>
          </div>
        </div>
        <div class="upload-box">
          <input :key="uploadKey" class="native-file-input" type="file" @change="handleUploadFile" />
          <div class="selected-file-card">
            <strong>{{ hasSelectedFile ? selectedFileName : "No file selected" }}</strong>
            <p>{{ hasSelectedFile ? `Size: ${selectedFileSize}` : "Choose a file before uploading." }}</p>
            <p>Supported types: {{ SUPPORTED_FILE_TYPES }}</p>
          </div>
          <el-button :disabled="!hasSelectedFile" :loading="uploadingAdminFile" type="primary" @click="submitUpload">
            Upload Shared Knowledge
          </el-button>
        </div>
      </article>

      <article class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Search</p>
            <h2>Retrieval Preview</h2>
          </div>
        </div>
        <div class="toolbar">
          <el-input v-model="searchText" placeholder="Enter a query to preview matching chunks" />
          <el-input-number v-model="searchK" :max="20" :min="1" />
          <el-button type="primary" @click="searchKnowledge">Search</el-button>
        </div>
        <div class="results-stack">
          <article v-for="result in knowledgeStore.adminSearchResults" :key="result.doc_id" class="result-card">
            <strong>{{ result.doc_id }}</strong>
            <p>{{ result.content }}</p>
          </article>
          <p v-if="knowledgeStore.adminSearchResults.length === 0" class="muted-copy">
            Search results will appear here.
          </p>
        </div>
      </article>
    </div>

    <article class="panel">
      <div class="panel-header">
        <div>
          <p class="panel-kicker">Inspect</p>
          <h2>Chunk Management</h2>
        </div>
      </div>

      <div class="toolbar">
        <el-input
          v-model="filterUserId"
          clearable
          placeholder="Optional user_id filter for scoped chunk inspection"
          @keydown.enter.prevent="applyFilter"
        />
        <el-button @click="applyFilter">Apply Filter</el-button>
      </div>

      <el-table :data="knowledgeStore.adminChunks" stripe v-loading="knowledgeStore.loading">
        <el-table-column label="doc_id" prop="doc_id" min-width="220" />
        <el-table-column label="source_file" min-width="180">
          <template #default="{ row }">
            {{ row.metadata.source_file || "unknown" }}
          </template>
        </el-table-column>
        <el-table-column label="user_id" min-width="160">
          <template #default="{ row }">
            {{ row.metadata.user_id || "__shared__" }}
          </template>
        </el-table-column>
        <el-table-column label="content" min-width="320">
          <template #default="{ row }">
            {{ row.content.slice(0, 120) }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="110">
          <template #default="{ row }">
            <el-button text type="danger" @click="deleteChunk(row.doc_id)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <p class="table-summary">
          Showing {{ pageStart }}-{{ pageEnd }} of {{ knowledgeStore.adminTotal }} chunk(s)
        </p>
        <el-pagination
          :current-page="knowledgeStore.adminCurrentPage"
          :page-size="knowledgeStore.adminPageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="knowledgeStore.adminTotal"
          background
          layout="total, sizes, prev, pager, next"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>

      <div class="toolbar">
        <el-input v-model="deleteDocId" placeholder="Delete a chunk by doc_id" />
        <el-button type="danger" @click="deleteChunk()">Delete Chunk</el-button>
      </div>
    </article>

    <article class="panel danger-panel">
      <div class="panel-header">
        <div>
          <p class="panel-kicker">Rebuild</p>
          <h2>Rebuild Vector Index</h2>
        </div>
      </div>
      <p class="warning-copy">
        This clears the current vector collection and reloads shared plus uploaded knowledge files.
      </p>
      <label class="checkbox-row">
        <input v-model="rebuildConfirmed" type="checkbox" />
        <span>I understand this will rebuild the active index.</span>
      </label>
      <el-button :disabled="!rebuildConfirmed" type="danger" @click="rebuildKnowledgeBase">
        Start Rebuild
      </el-button>
    </article>
  </section>
</template>
