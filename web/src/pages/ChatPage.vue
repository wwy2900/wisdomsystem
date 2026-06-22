<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import { useChatStore } from "@/stores/chat";
import { useKnowledgeStore } from "@/stores/knowledge";
import { useSessionStore } from "@/stores/session";
import { groupChunksBySourceFile } from "@/utils/groupChunks";

const SUPPORTED_FILE_TYPES = "txt, pdf, docx, xlsx, csv, md, json";

const sessionStore = useSessionStore();
const chatStore = useChatStore();
const knowledgeStore = useKnowledgeStore();

const prompt = ref("");
const selectedFile = ref<File | null>(null);
const uploadInputKey = ref(0);
const uploadingPrivateFile = ref(false);

const groupedFiles = computed(() => groupChunksBySourceFile(knowledgeStore.privateChunks));
const hasSelectedFile = computed(() => Boolean(selectedFile.value));
const selectedFileName = computed(() => selectedFile.value?.name ?? "");
const selectedFileSize = computed(() => (selectedFile.value ? formatFileSize(selectedFile.value.size) : ""));

function formatFileSize(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function resetSelectedFile() {
  selectedFile.value = null;
  uploadInputKey.value += 1;
}

async function bootstrap() {
  await Promise.all([sessionStore.refresh(), knowledgeStore.refreshPrivateChunks()]);
  if (sessionStore.currentSessionId) {
    await chatStore.loadSession(sessionStore.currentSessionId);
  }
}

async function switchSession(sessionId: string) {
  sessionStore.setCurrentSession(sessionId);
  await chatStore.loadSession(sessionId);
}

async function createSession() {
  const sessionId = await sessionStore.create();
  chatStore.reset();
  sessionStore.setCurrentSession(sessionId);
}

async function sendMessage() {
  const value = prompt.value.trim();
  if (!value || chatStore.isStreaming) {
    return;
  }

  prompt.value = "";

  try {
    await chatStore.sendMessage(value);
  } catch {
    prompt.value = chatStore.lastFailedPrompt || value;
  }
}

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  selectedFile.value = target.files?.[0] ?? null;
}

async function uploadPrivateFile() {
  if (!selectedFile.value || uploadingPrivateFile.value) {
    return;
  }

  uploadingPrivateFile.value = true;

  try {
    const result = await knowledgeStore.uploadPrivateFile(selectedFile.value);
    ElMessage.success(
      result.skipped
        ? `Upload skipped: ${result.reason || "duplicate or unsupported file"}`
        : `Private knowledge updated with ${result.chunk_count} chunk(s).`,
    );
    resetSelectedFile();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Private upload failed.");
  } finally {
    uploadingPrivateFile.value = false;
  }
}

async function deletePrivateFile(docIds: string[]) {
  try {
    for (const docId of docIds) {
      await knowledgeStore.deletePrivateChunk(docId);
    }
    ElMessage.success("Private file removed.");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Delete failed.");
  }
}

onMounted(() => {
  bootstrap().catch((error) => {
    ElMessage.error(error instanceof Error ? error.message : "Page initialization failed.");
  });
});
</script>

<template>
  <section class="chat-layout">
    <aside class="panel session-panel">
      <div class="panel-header">
        <div>
          <p class="panel-kicker">Sessions</p>
          <h2>Chat Sessions</h2>
        </div>
        <el-button type="primary" @click="createSession">New Session</el-button>
      </div>

      <div class="session-list">
        <button
          v-for="session in sessionStore.sessions"
          :key="session.session_id"
          class="session-item"
          :class="{ active: session.session_id === sessionStore.currentSessionId }"
          type="button"
          @click="switchSession(session.session_id)"
        >
          <strong>{{ session.preview || "Empty session" }}</strong>
          <span>{{ session.saved_at || "Not saved yet" }}</span>
        </button>
      </div>
    </aside>

    <div class="panel chat-panel">
      <div class="panel-header">
        <div>
          <p class="panel-kicker">Assistant</p>
          <h2>Chat Workspace</h2>
        </div>
        <div class="status-pill">
          {{ chatStore.isStreaming ? "Streaming response" : "Connected to FastAPI" }}
        </div>
      </div>

      <div class="message-list">
        <article v-for="(message, index) in chatStore.messages" :key="`${message.role}-${index}`" class="message-card">
          <header>{{ message.role === "assistant" ? "Assistant" : "User" }}</header>
          <p>{{ message.content }}</p>
        </article>

        <article v-if="chatStore.streamingAssistantText" class="message-card assistant-stream">
          <header>Assistant</header>
          <p>{{ chatStore.streamingAssistantText }}</p>
        </article>
      </div>

      <el-collapse v-if="chatStore.toolEvents.length" class="thoughts-block">
        <el-collapse-item title="Tool Trace">
          <pre>{{ chatStore.toolEvents.join("\n") }}</pre>
        </el-collapse-item>
      </el-collapse>

      <div class="composer">
        <el-input
          v-model="prompt"
          :rows="4"
          type="textarea"
          placeholder="Ask a question, then continue with the current session or your private knowledge."
          @keydown.ctrl.enter.prevent="sendMessage"
        />
        <div class="composer-actions">
          <small>Press `Ctrl + Enter` to send.</small>
          <el-button :loading="chatStore.isStreaming" type="primary" @click="sendMessage">Send</el-button>
        </div>
      </div>
    </div>

    <aside class="panel private-knowledge-panel">
      <div class="panel-header">
        <div>
          <p class="panel-kicker">Private Knowledge</p>
          <h2>My Files</h2>
        </div>
      </div>

      <div class="upload-box">
        <input :key="uploadInputKey" class="native-file-input" type="file" @change="handleFileChange" />
        <div class="selected-file-card">
          <strong>{{ hasSelectedFile ? selectedFileName : "No file selected" }}</strong>
          <p>{{ hasSelectedFile ? `Size: ${selectedFileSize}` : "Choose a file before uploading." }}</p>
          <p>Supported types: {{ SUPPORTED_FILE_TYPES }}</p>
        </div>
        <el-button :disabled="!hasSelectedFile" :loading="uploadingPrivateFile" type="primary" @click="uploadPrivateFile">
          Upload to Private Knowledge
        </el-button>
      </div>

      <div class="file-list">
        <article v-for="group in groupedFiles" :key="group.fileName" class="file-card">
          <div>
            <strong>{{ group.fileName }}</strong>
            <p>{{ group.chunks.length }} chunk(s)</p>
          </div>
          <el-button text type="danger" @click="deletePrivateFile(group.chunks.map((chunk) => chunk.doc_id))">
            Delete
          </el-button>
        </article>

        <p v-if="groupedFiles.length === 0" class="muted-copy">
          No private files yet. Upload one to keep its chunks available to this account only.
        </p>
      </div>
    </aside>
  </section>
</template>
