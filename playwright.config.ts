import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 300_000,
  use: { trace: "retain-on-failure" },
  webServer: {
    command: "npm.cmd run dev:frontend -- --port 5174",
    url: "http://127.0.0.1:5174",
    env: { VITE_API_URL: "http://127.0.0.1:8765" },
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
