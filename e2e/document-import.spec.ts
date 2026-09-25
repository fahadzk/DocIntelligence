import { _electron as electron, expect, test } from "@playwright/test";
import { existsSync, mkdtempSync } from "node:fs";
import { freemem, tmpdir } from "node:os";
import path from "node:path";

test("desktop imports and retains a document after restart", async () => {
  const dataDir = mkdtempSync(path.join(tmpdir(), "document-intelligence-e2e-"));
  const modelDir = process.env.DOCUMENT_INTELLIGENCE_E2E_USE_MODEL === "1" || freemem() >= 3_500_000_000
    ? path.join(process.cwd(), "data", "models")
    : path.join(dataDir, "models");
  const hasAnswerModel = existsSync(path.join(modelDir, "answers", "qwen2.5-1.5b-instruct-q4_k_m.gguf"));
  const environment = {
    ...process.env,
    PYTHON_EXECUTABLE: path.join(process.cwd(), ".venv", "Scripts", "python.exe"),
    DOCUMENT_INTELLIGENCE_DATA_DIR: dataDir,
    DOCUMENT_INTELLIGENCE_MODEL_DIR: modelDir,
    DOCUMENT_INTELLIGENCE_PORT: "8765",
    DOCUMENT_INTELLIGENCE_SOFTWARE_RENDERING: "1",
    VITE_DEV_SERVER_URL: "http://127.0.0.1:5174",
  };
  const launch = () => electron.launch({ args: [".", "--no-sandbox"], cwd: process.cwd(), env: environment });
  const first = await launch();
  const window = await first.firstWindow({ timeout: 90_000 });
  await expect(window.getByText("New project")).toBeVisible({ timeout: 45_000 });
  await window.getByText("New project").click();
  await window.getByPlaceholder("e.g. Case Files").fill("Desktop test");
  await window.getByText("Create project").click();
  await expect(window.getByRole("heading", { name: "Desktop test", level: 1 })).toBeVisible();
  await window.getByRole("button", { name: "Collapse sidebar" }).click();
  await expect(window.locator(".app-shell")).toHaveClass(/sidebar-unpinned/);
  await expect.poll(() => window.locator(".sidebar").evaluate((item) => item.getBoundingClientRect().width)).toBeLessThan(60);
  await expect.poll(() => window.locator(".project-list").evaluate((item) => getComputedStyle(item).scrollbarWidth)).toBe("none");
  await expect(window.getByRole("button", { name: "Pin sidebar open" })).toBeHidden();
  await window.screenshot({ path: "test-results/sidebar-collapsed.png" });
  await window.evaluate(() => { const extra = document.createElement("button"); extra.className = "project test-other-project"; extra.textContent = "Another project"; document.querySelector(".project-list")?.appendChild(extra); });
  await expect(window.locator(".test-other-project")).toBeHidden();
  await window.evaluate(() => document.querySelector(".test-other-project")?.remove());
  await window.getByRole("button", { name: "Switch project, current Desktop test" }).click();
  await expect(window.locator(".app-shell")).not.toHaveClass(/sidebar-unpinned/);
  await window.getByRole("button", { name: "Collapse sidebar" }).click();
  await window.locator(".sidebar").hover();
  await expect.poll(() => window.locator(".sidebar").evaluate((item) => item.getBoundingClientRect().width)).toBeGreaterThan(230);
  await expect.poll(() => window.locator(".project-list").evaluate((item) => getComputedStyle(item).scrollbarWidth)).toBe("thin");
  await window.screenshot({ path: "test-results/sidebar-peek.png" });
  await window.getByRole("button", { name: "Pin sidebar open" }).click();
  await expect(window.locator(".app-shell")).not.toHaveClass(/sidebar-unpinned/);
  await expect(window.getByRole("button", { name: "Pin sidebar open" })).toBeHidden();
  await window.evaluate(() => { const list = document.querySelector(".project-list"); for (let index = 0; index < 30; index++) { const row = document.createElement("div"); row.className = "test-project-overflow"; row.style.height = "35px"; list?.appendChild(row); } });
  await expect(window.getByRole("button", { name: "Settings" })).toBeInViewport();
  await window.screenshot({ path: "test-results/sidebar-many-projects.png" });
  await window.evaluate(() => document.querySelectorAll(".test-project-overflow").forEach((row) => row.remove()));
  await window.getByRole("button", { name: "Settings" }).click();
  await window.getByRole("radio", { name: /Dark/ }).check();
  await expect.poll(() => window.evaluate(() => document.documentElement.dataset.theme)).toBe("dark");
  await window.screenshot({ path: "test-results/theme-dark-settings.png" });
  await window.getByRole("radio", { name: /Light/ }).check();
  await expect.poll(() => window.evaluate(() => document.documentElement.dataset.theme)).toBe("light");
  await window.screenshot({ path: "test-results/theme-light-settings.png" });
  await window.getByRole("radio", { name: /System/ }).check();
  await expect(window.getByRole("radio", { name: /System/ })).toBeChecked();
  await window.getByRole("navigation", { name: "Workspace navigation" }).getByRole("button", { name: "Documents" }).click();
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
  await window.getByRole("navigation", { name: "Workspace navigation" }).getByRole("button", { name: "Search" }).click();
  await window.getByLabel("Search terms").fill("imported source");
  await window.getByRole("button", { name: "Search", exact: true }).last().click();
  await expect(window.getByText("An imported source paragraph.")).toBeVisible();
  await expect(window.locator(".match-type").first()).toContainText("Exact");
  await window.screenshot({ path: "test-results/phase3-search.png" });
  await window.getByRole("button", { name: "Pipeline Lab" }).click();
  await expect(window.getByRole("heading", { name: "Pipeline Lab" })).toBeVisible();
  await expect(window.getByText("BGE Small / FastEmbed").first()).toBeVisible();
  await window.getByRole("button", { name: "Preview Chunks" }).click();
  await expect(window.getByText(/chunks? · .* characters on average/)).toBeVisible();
  await window.screenshot({ path: "test-results/pipeline-lab-document.png" });
  await window.getByRole("button", { name: "SEARCH", exact: true }).click();
  await window.getByLabel("Search this project").fill("Europa");
  await expect.poll(async () => {
    const projects = await (await fetch("http://127.0.0.1:8765/api/projects")).json() as { id: string }[];
    const states = await (await fetch(`http://127.0.0.1:8765/api/projects/${projects[0].id}/pipeline/index/status`)).json() as { status: string }[];
    return states.length === 2 && states.every((item) => item.status === "ready");
  }, { timeout: 120_000 }).toBe(true);
  await window.locator(".pipeline-lab .search-form").getByRole("button", { name: "Search" }).click();
  await expect(window.getByText("Keyword BM25").first()).toBeVisible();
  await window.screenshot({ path: "test-results/pipeline-lab-search.png" });
  await window.getByRole("button", { name: "ASK", exact: true }).click();
  await expect(window.getByLabel("Grounding")).toHaveValue("sources_only");
  await expect(window.getByText("Inspect Context")).toHaveCount(0);
  await window.getByLabel("Evidence passages").fill("2");
  await expect(window.getByText("All changes saved")).toBeVisible({ timeout: 15_000 });
  await expect.poll(async () => {
    const projects = await (await fetch("http://127.0.0.1:8765/api/projects")).json() as { id: string }[];
    const saved = await (await fetch(`http://127.0.0.1:8765/api/projects/${projects[0].id}/pipeline`)).json() as { effective: { ask: { evidence_count: number } } };
    return saved.effective.ask.evidence_count;
  }).toBe(2);
  await window.setViewportSize({ width: 480, height: 800 });
  await expect(window.getByText("Desktop test").first()).toBeVisible();
  await expect.poll(() => window.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  await window.screenshot({ path: "test-results/pipeline-lab-narrow.png" });
  await window.setViewportSize({ width: 1280, height: 800 });
  await window.screenshot({ path: "test-results/pipeline-lab-ask.png" });
  await window.getByRole("navigation", { name: "Workspace navigation" }).getByRole("button", { name: "Search" }).click();
  await expect(window.getByLabel("Search terms")).toBeVisible();
  await expect(window.getByText("An imported source paragraph.")).toBeVisible();
  await window.getByRole("navigation", { name: "Workspace navigation" }).getByRole("button", { name: "Ask" }).click();
  if (hasAnswerModel) {
    await window.locator("#project-ask-query").fill("Which planet does Europa orbit?");
    await window.getByRole("button", { name: "Ask", exact: true }).last().click();
    await expect(window.getByText("Supporting passages")).toBeVisible({ timeout: 120_000 });
    await expect(window.locator("#evidence-1").getByText("Europa is a moon of Jupiter. It orbits the giant planet every 3.5 days.")).toBeVisible();
    await window.screenshot({ path: "test-results/phase3-answer.png" });
    await window.locator("#project-ask-query").fill("Can I continue after the answer?");
    await expect(window.locator("#project-ask-query")).toHaveValue("Can I continue after the answer?");
  } else {
    await expect(window.getByText("Local answer model", { exact: true })).toBeVisible();
  }
  await window.getByRole("navigation", { name: "Workspace navigation" }).getByRole("button", { name: "Documents" }).click();
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
  await expect(reopened.getByText("An imported source paragraph.").first()).toBeVisible();
  await reopened.getByRole("navigation", { name: "Workspace navigation" }).getByRole("button", { name: "Search" }).click();
  await reopened.getByLabel("Search terms").fill("imported");
  await reopened.getByRole("button", { name: "Search", exact: true }).last().click();
  await expect(reopened.locator(".evidence-item").getByText("An imported source paragraph.")).toBeVisible();
  await second.close();
});
