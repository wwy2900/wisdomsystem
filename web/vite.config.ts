import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";

const projectRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig(({ mode }) => {
  const useElementPlusPlugins = mode !== "test";

  return {
    root: projectRoot,
    plugins: [
      vue(),
      ...(useElementPlusPlugins
        ? [
            AutoImport({
              dts: false,
              resolvers: [ElementPlusResolver()],
            }),
            Components({
              dts: false,
              resolvers: [ElementPlusResolver()],
            }),
          ]
        : []),
    ],
    resolve: {
      alias: {
        "@": path.resolve(projectRoot, "./src"),
      },
    },
    build: {
      chunkSizeWarningLimit: 950,
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
        "/health": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    test: {
      root: projectRoot,
      environment: "jsdom",
      globals: true,
      include: ["src/**/*.spec.ts"],
      exclude: ["tests/e2e/**", "node_modules/**", "dist/**"],
    },
  };
});
