export {};
declare global {
  interface Window {
    documentIntelligence?: {
      openOriginal: (projectId: string, documentId: string, fileType: string) => Promise<string>;
    };
  }
}
