/** Large-text mode: the choice is remembered per browser when storage is available. */
export type TextSize = "normal" | "large";

const STORAGE_KEY = "seculayer.textSize";

export function readTextSize(): TextSize {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "large" ? "large" : "normal";
  } catch {
    return "normal";
  }
}

export function writeTextSize(size: TextSize): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, size);
  } catch {
    // Storage is blocked (private window, cleared site data): the choice lasts for this page only.
  }
}

export function applyTextSize(size: TextSize): void {
  document.documentElement.dataset.textSize = size;
}
