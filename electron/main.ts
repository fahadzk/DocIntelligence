import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import { ChildProcess, spawn, spawnSync } from "node:child_process";
import path from "node:path";
import fs from "node:fs";

const backendPort = Number(process.env.DOCUMENT_INTELLIGENCE_PORT ?? "8000");
const BACKEND_URL = `http://127.0.0.1:${backendPort}`;
let backend: ChildProcess | undefined;
const projectRoot = path.resolve(__dirname, "..");
const dataDir = process.env.DOCUMENT_INTELLIGENCE_DATA_DIR ??
  (app.isPackaged ? path.join(app.getPath("userData"), "data") : path.join(projectRoot, "data"));

async function waitForBackend(): Promise<void> {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try { const response = await fetch(`${BACKEND_URL}/health`); if (response.ok && (await response.json()).service === "document-intelligence-backend") return; } catch { /* backend is starting */ }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("The local service did not become ready.");
}

function startBackend(): void {
  const python = process.env.PYTHON_EXECUTABLE ?? path.join(projectRoot, ".venv", "Scripts", "python.exe");
  backend = spawn(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(backendPort)], {
    cwd: path.join(projectRoot, "backend"), windowsHide: true, stdio: "pipe",
    env: { ...process.env, DOCUMENT_INTELLIGENCE_DATA_DIR: dataDir }
  });
  backend.stderr?.on("data", (data) => console.error(`[backend] ${data}`));
}

async function createWindow(): Promise<void> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    if (!response.ok || (await response.json()).service !== "document-intelligence-backend") startBackend();
  } catch { startBackend(); }
  try { await waitForBackend(); }
  catch (error) { await dialog.showErrorBox("Document Intelligence", error instanceof Error ? error.message : "Unable to start local service."); app.quit(); return; }
  const window = new BrowserWindow({ width: 1280, height: 820, minWidth: 1000, minHeight: 650, title: "Document Intelligence", webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, preload: path.join(__dirname, "preload.js") } });
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(`${BACKEND_URL}/api/projects/`) && url.includes("/original#page=")) void shell.openExternal(url);
    return { action: "deny" };
  });
  await window.loadURL(app.isPackaged ? BACKEND_URL : (process.env.VITE_DEV_SERVER_URL ?? "http://127.0.0.1:5173"));
}

ipcMain.handle("open-original", async (_event, projectId: string, documentId: string, fileType: string) => {
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuid.test(projectId) || !uuid.test(documentId) || !["pdf", "docx", "txt", "md"].includes(fileType)) return "Invalid document reference.";
  const original = path.join(dataDir, "documents", projectId, documentId, `original.${fileType}`);
  if (!fs.existsSync(original)) return "The retained original is missing.";
  return shell.openPath(original);
});

app.whenReady().then(createWindow);
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("before-quit", () => {
  if (!backend?.pid) return;
  if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(backend.pid), "/T", "/F"], { windowsHide: true });
  else backend.kill("SIGTERM");
});
