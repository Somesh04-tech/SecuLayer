import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Tests marked `@vitest-environment node` (the design-token scan) have no DOM to set up.
if (typeof window !== "undefined") {
  afterEach(() => {
    cleanup();
    delete document.documentElement.dataset.textSize;
    try {
      window.localStorage.clear();
    } catch {
      // Some tests make storage throw on purpose.
    }
  });

  // jsdom doesn't implement these; the shell and Radix call them.
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
