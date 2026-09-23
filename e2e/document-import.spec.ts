import { _electron as electron, expect, test } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

test("desktop imports and retains a document after restart", async () => {
  const dataDir = mkdtempSync(path.join(tmpdir(), "document-intelligence-e2e-"));
  const environment = {
    ...process.env,
    PYTHON_EXECUTABLE: path.join(process.cwd(), ".venv", "Scripts", "python.exe"),
    DOCUMENT_INTELLIGENCE_DATA_DIR: dataDir,
    DOCUMENT_INTELLIGENCE_PORT: "8765",
    VITE_DEV_SERVER_URL: "http://127.0.0.1:5174",
  };
  const launch = () => electron.launch({ args: ["."], cwd: process.cwd(), env: environment });
  const first = await launch();
  const window = await first.firstWindow();
  await expect(window.getByText("+ New project")).toBeVisible();
  await window.getByText("+ New project").click();
  await window.getByPlaceholder("e.g. Case Files").fill("Desktop test");
  await window.getByText("Create project").click();
  await expect(window.getByRole("heading", { name: "Desktop test", level: 1 })).toBeVisible();
  await window.getByLabel("Choose documents").setInputFiles({
    name: "sample.txt", mimeType: "text/plain", buffer: Buffer.from("An imported source paragraph."),
  });
  await expect(window.getByText("An imported source paragraph.")).toBeVisible();
  await window.screenshot({ path: "test-results/phase2-reading.png" });
  await window.getByLabel("Choose documents").setInputFiles({
    name: "broken.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-broken"),
  });
  await expect(window.getByText("Could not process this document")).toBeVisible();
  await window.screenshot({ path: "test-results/phase2-failure.png" });
  await window.getByText("Delete document").click();
  await window.getByRole("button", { name: "Delete document" }).last().click();
  await expect(window.getByText("broken.pdf")).toHaveCount(0);
  await first.close();
  await expect.poll(async () => {
    try { await fetch("http://127.0.0.1:8765/health"); return true; }
    catch { return false; }
  }, { timeout: 10_000 }).toBe(false);
  const second = await launch();
  const reopened = await second.firstWindow();
  await expect(reopened.getByRole("heading", { name: "Desktop test", level: 1 })).toBeVisible();
  await reopened.getByText("sample.txt").first().click();
  await expect(reopened.getByText("An imported source paragraph.")).toBeVisible();
  await second.close();
});
