import { useEffect, useLayoutEffect, useState } from "react";

export type ThemePreference = "light" | "dark" | "system";
const STORAGE_KEY = "document-intelligence.theme";

function storedPreference(): ThemePreference {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (value === "light" || value === "dark" || value === "system") return value;
  } catch { /* Private or unavailable storage: use the system preference. */ }
  return "system";
}

function systemIsDark(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function useAppearance() {
  const [preference, setPreference] = useState<ThemePreference>(storedPreference);
  const [darkSystem, setDarkSystem] = useState(systemIsDark);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const update = (event: MediaQueryListEvent) => setDarkSystem(event.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useLayoutEffect(() => {
    const resolved = preference === "system" ? (darkSystem ? "dark" : "light") : preference;
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
    try { window.localStorage.setItem(STORAGE_KEY, preference); } catch { /* Keep the in-memory choice. */ }
  }, [preference, darkSystem]);

  return { preference, setPreference };
}
