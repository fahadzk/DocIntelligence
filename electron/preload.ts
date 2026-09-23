import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("documentIntelligence", {
  openOriginal: (projectId: string, documentId: string, fileType: string) =>
    ipcRenderer.invoke("open-original", projectId, documentId, fileType) as Promise<string>
});
