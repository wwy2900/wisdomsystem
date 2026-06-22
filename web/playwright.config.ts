import { defineConfig } from "@playwright/test";

const webServer = process.env.PLAYWRIGHT_NO_WEBSERVER
  ? undefined
  : {
      command: "npm run preview -- --host 127.0.0.1 --port 4173",
      port: 4173,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    };

export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: "http://127.0.0.1:4173",
    browserName: "chromium",
    channel: "msedge",
    trace: "on-first-retry",
  },
  webServer,
});
