// @vitest-environment node
/**
 * docs/PLAN.md §9 M8: src/content/sources.ts contains exactly the URLs in §12.
 *
 * §12 gives MITRE ATLAS technique pages as the pattern `https://atlas.mitre.org/techniques/<ID>`.
 * The extraction stops at "<", so the pattern becomes its base URL, which sources.ts lists.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  ATLAS_TECHNIQUES,
  QUOTES,
  SOURCES,
  allSourceUrls,
  sourceById,
} from "../src/content/sources";

const PLAN = fileURLToPath(new URL("../../docs/PLAN.md", import.meta.url));

function planUrls(): string[] {
  const text = readFileSync(PLAN, "utf-8");
  const start = text.indexOf("## 12. Sources");
  const end = text.indexOf("## 13.");
  expect(start).toBeGreaterThan(0);
  expect(end).toBeGreaterThan(start);
  const section = text.slice(start, end);
  return [...section.matchAll(/https?:\/\/[^\s`)<>|]+/g)].map((m) => m[0].replace(/[.,;:]+$/, ""));
}

describe("sources.ts", () => {
  it("contains exactly the URLs in PLAN §12", () => {
    const fromPlan = planUrls();
    expect(fromPlan.length).toBeGreaterThan(50);
    expect(new Set(allSourceUrls())).toEqual(new Set(fromPlan));
  });

  it("lists each URL once", () => {
    const urls = allSourceUrls();
    expect(urls.length).toBe(new Set(urls).size);
  });

  it("has unique ids, and every quote points at a real source", () => {
    const ids = SOURCES.map((s) => s.id);
    expect(ids.length).toBe(new Set(ids).size);
    for (const quote of Object.values(QUOTES)) {
      expect(() => sourceById(quote.sourceId)).not.toThrow();
    }
  });

  it("credits Llama", () => {
    const credit = SOURCES.filter((s) => s.group === "credit");
    expect(credit.map((s) => s.note).join(" ")).toMatch(/Built with Llama/);
    expect(credit.map((s) => s.note).join(" ")).toMatch(/Llama 4 Community License/);
  });

  it("names the ATLAS techniques the demo uses", () => {
    expect(ATLAS_TECHNIQUES.map((t) => t.id)).toContain("AML.T0051");
  });
});
