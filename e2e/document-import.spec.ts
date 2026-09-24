import { _electron as electron, expect, test } from "@playwright/test";
import { existsSync, mkdtempSync } from "node:fs";
import { freemem, tmpdir } from "node:os";
import path from "node:path";

test("desktop imports and retains a document after restart", async () => {
  const dataDir = mkdtempSync(path.join(tmpdir(), "document-intelligence-e2e-"));
  const modelDir = freemem() >= 3_500_000_000
    ? path.join(process.cwd(), "data", "models")
    : path.join(dataDir, "models");
  const hasAnswerModel = existsSync(path.join(modelDir, "answers", "qwen2.5-1.5b-instruct-q4_k_m.gguf"));
  const environment = {
    ...process.env,
    PYTHON_EXECUTABLE: path.join(process.cwd(), ".venv", "Scripts", "python.exe"),
    DOCUMENT_INTELLIGENCE_DATA_DIR: dataDir,
    DOCUMENT_INTELLIGENCE_MODEL_DIR: modelDir,
    DOCUMENT_INTELLIGENCE_PORT: "8765",
    VITE_DEV_SERVER_URL: "http://127.0.0.1:5174",
  };
  const launch = () => electron.launch({ args: ["."], cwd: process.cwd(), env: environment });
  const first = await launch();
  const window = await first.firstWindow({ timeout: 90_000 });
  await expect(window.getByText("+ New project")).toBeVisible({ timeout: 45_000 });
  await window.getByText("+ New project").click();
  await window.getByPlaceholder("e.g. Case Files").fill("Desktop test");
  await window.getByText("Create project").click();
  await expect(window.getByRole("heading", { name: "Desktop test", level: 1 })).toBeVisible();
  await window.getByLabel("Choose documents").setInputFiles({
    name: "sample.txt", mimeType: "text/plain", buffer: Buffer.from("An imported source paragraph."),
  });
  await expect(window.getByText("An imported source paragraph.")).toBeVisible({ timeout: 30_000 });
  await window.getByLabel("Choose documents").setInputFiles({
    name: "fact.txt", mimeType: "text/plain", buffer: Buffer.from("Europa is a moon of Jupiter. It orbits the giant planet every 3.5 days."),
  });
  await expect(window.getByText("Europa is a moon of Jupiter. It orbits the giant planet every 3.5 days.")).toBeVisible({ timeout: 30_000 });
  await expect.poll(async () => {
    const projects = await (await fetch("http://127.0.0.1:8765/api/projects")).json() as { id: string }[];
    const states = await (await fetch(`http://127.0.0.1:8765/api/projects/${projects[0].id}/index/status`)).json() as { status: string }[];
    return states.length === 2 && states.every((item) => item.status === "ready");
  }, { timeout: 120_000 }).toBe(true);
  await window.getByRole("button", { name: "Search", exact: true }).click();
  await window.getByLabel("Search terms").fill("imported source");
  await window.getByRole("button", { name: "Search", exact: true }).last().click();
  await expect(window.getByText("An imported source paragraph.")).toBeVisible();
  await expect(window.locator(".match-type").first()).toContainText("Exact");
  await window.screenshot({ path: "test-results/phase3-search.png" });
  await window.getByRole("button", { name: "Ask", exact: true }).click();
  if (hasAnswerModel) {
    await window.getByLabel("Question").fill("Which planet does Europa orbit?");
    await window.getByRole("button", { name: "Ask", exact: true }).last().click();
    await expect(window.getByText("Supporting passages")).toBeVisible({ timeout: 120_000 });
    await expect(window.getByText("Europa is a moon of Jupiter. It orbits the giant planet every 3.5 days.")).toBeVisible();
    await window.screenshot({ path: "test-results/phase3-answer.png" });
  } else {
    await expect(window.getByText("Local answer model")).toBeVisible();
  }
  await window.getByRole("button", { name: "Documents", exact: true }).click();
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
  const reopened = await second.firstWindow({ timeout: 90_000 });
  await expect(reopened.getByRole("heading", { name: "Desktop test", level: 1 })).toBeVisible({ timeout: 45_000 });
  await reopened.getByText("sample.txt").first().click();
  await expect(reopened.getByText("An imported source paragraph.")).toBeVisible();
  await reopened.getByRole("button", { name: "Search", exact: true }).click();
  await reopened.getByLabel("Search terms").fill("imported");
  await reopened.getByRole("button", { name: "Search", exact: true }).last().click();
  await expect(reopened.getByText("An imported source paragraph.")).toBeVisible();
  await second.close();
});
