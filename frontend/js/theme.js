const STORAGE_KEY = "hazardmap-theme";
const listeners = new Set();

export function getTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function applyTheme(theme, { persist = false } = {}) {
  const next = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  if (persist) {
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }
  for (const listener of listeners) listener(next);
}

export function toggleTheme() {
  applyTheme(getTheme() === "dark" ? "light" : "dark", { persist: true });
}

export function onThemeChange(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function syncThemeButton(button) {
  if (!button) return;
  const dark = getTheme() === "dark";
  button.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  button.setAttribute("aria-pressed", dark ? "true" : "false");
}

export function applyTileTheme(layer, theme) {
  const container = layer?.getContainer?.();
  if (!container) return;
  container.classList.toggle("osm-dim", theme === "dark");
}
