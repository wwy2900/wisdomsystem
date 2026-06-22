import { defineStore } from "pinia";

import * as knowledgeApi from "@/api/knowledge";
import type { KnowledgeChunk } from "@/types";

export const useKnowledgeStore = defineStore("knowledge", {
  state: () => ({
    privateChunks: [] as KnowledgeChunk[],
    adminChunks: [] as KnowledgeChunk[],
    adminSearchResults: [] as KnowledgeChunk[],
    adminTotal: 0,
    adminCurrentPage: 1,
    adminPageSize: 20,
    adminFilterUserId: "",
    loading: false,
  }),
  actions: {
    async refreshPrivateChunks() {
      const response = await knowledgeApi.listPrivateChunks();
      this.privateChunks = response.chunks;
    },
    async uploadPrivateFile(file: File) {
      const result = await knowledgeApi.uploadPrivateDocument(file);
      await this.refreshPrivateChunks();
      return result;
    },
    async deletePrivateChunk(docId: string) {
      const result = await knowledgeApi.deletePrivateChunk(docId);
      await this.refreshPrivateChunks();
      return result;
    },
    setAdminPage(page: number) {
      this.adminCurrentPage = Math.max(1, page);
    },
    setAdminPageSize(pageSize: number) {
      this.adminPageSize = Math.min(200, Math.max(1, pageSize));
    },
    setAdminFilterUserId(userId: string) {
      this.adminFilterUserId = userId.trim();
      this.adminCurrentPage = 1;
    },
    async refreshAdminChunks(options?: { page?: number; pageSize?: number; userId?: string }) {
      if (options?.page !== undefined) {
        this.setAdminPage(options.page);
      }
      if (options?.pageSize !== undefined) {
        this.setAdminPageSize(options.pageSize);
      }
      if (options?.userId !== undefined) {
        this.adminFilterUserId = options.userId.trim();
      }

      this.loading = true;
      try {
        const loadPage = () =>
          knowledgeApi.listAdminChunks(
            this.adminPageSize,
            (this.adminCurrentPage - 1) * this.adminPageSize,
            this.adminFilterUserId || undefined,
          );

        let response = await loadPage();
        const maxPage = Math.max(1, Math.ceil(response.total / this.adminPageSize));

        if (this.adminCurrentPage > maxPage) {
          this.adminCurrentPage = maxPage;
          response = await loadPage();
        }

        this.adminChunks = response.chunks;
        this.adminTotal = response.total;
      } finally {
        this.loading = false;
      }
    },
    async searchAdmin(query: string, k = 5, userId?: string) {
      const response = await knowledgeApi.searchAdminChunks(query, k, (userId ?? this.adminFilterUserId) || undefined);
      this.adminSearchResults = response.results;
    },
    async uploadAdminFile(file: File) {
      const result = await knowledgeApi.uploadAdminDocument(file);
      return result;
    },
    async deleteAdminChunk(docId: string, userId?: string) {
      const result = await knowledgeApi.deleteAdminChunk(docId, userId);
      return result;
    },
    async rebuild() {
      return knowledgeApi.rebuildKnowledge();
    },
    clear() {
      this.privateChunks = [];
      this.adminChunks = [];
      this.adminSearchResults = [];
      this.adminTotal = 0;
      this.adminCurrentPage = 1;
      this.adminPageSize = 20;
      this.adminFilterUserId = "";
      this.loading = false;
    },
  },
});
