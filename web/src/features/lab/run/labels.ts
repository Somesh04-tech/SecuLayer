/** "Dana" → "Dana", "the customer" → "The customer". */
export function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** The host of an absolute URL, or "" for a relative one. */
export function hostOf(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.hostname;
  } catch {
    return "";
  }
}

/** True for a relative URL or one on this server. */
export function isLocal(url: string): boolean {
  if (!/^[a-z][a-z0-9+.-]*:/i.test(url) && !url.startsWith("//")) return true;
  try {
    return new URL(url, window.location.href).origin === window.location.origin;
  } catch {
    return false;
  }
}
