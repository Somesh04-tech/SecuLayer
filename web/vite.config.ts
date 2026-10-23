import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8765" },
  },
  build: {
    outDir: "dist",
    // The server's CSP allows fonts and images only from 'self', so never inline assets as data: URIs.
    assetsInlineLimit: 0,
  },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.{ts,tsx}"],
    setupFiles: ["./tests/setup.ts"],
    pool: "threads",
    maxWorkers: 2,
    restoreMocks: true,
    unstubGlobals: true,
  },
});
