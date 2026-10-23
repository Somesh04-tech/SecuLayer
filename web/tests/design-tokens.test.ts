// @vitest-environment node
/**
 * Enforces docs/PLAN.md §4.6: every colour and font comes from src/styles/tokens.css.
 * Anywhere else in src, raw colour values, font-family declarations and Tailwind's default
 * palette, radius and shadow classes are errors.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const SRC = join(WEB, "src");
const TOKENS = join(SRC, "styles", "tokens.css");
const SCANNED = /\.(ts|tsx|js|jsx|css|html)$/;

const PALETTE =
  "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white";

const FORBIDDEN: { name: string; pattern: RegExp }[] = [
  {
    name: "hex colour",
    pattern: /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])/,
  },
  { name: "rgb()/rgba()", pattern: /\brgba?\(/ },
  { name: "hsl()/hsla()", pattern: /\bhsla?\(/ },
  { name: "oklch()/oklab()/lab()/lch()/color()", pattern: /\b(?:oklch|oklab|lab|lch|color)\(/ },
  { name: "font-family declaration", pattern: /font-family\s*:|fontFamily\b/ },
  { name: "arbitrary font utility", pattern: /\bfont-\[/ },
  {
    name: "default Tailwind palette class",
    pattern: new RegExp(
      `\\b(?:bg|text|border(?:-[trblxy])?|ring|ring-offset|outline|fill|stroke|from|via|to|shadow|divide|accent|caret|decoration|placeholder)-(?:${PALETTE})(?:-\\d{2,3})?(?![\\w-])`,
    ),
  },
  {
    name: "default Tailwind radius class",
    pattern: /\brounded(?:-[trblse]{1,2})?-(?:xs|sm|md|lg|xl|2xl|3xl|4xl|full)\b/,
  },
  { name: "default Tailwind shadow class", pattern: /\bshadow-(?:2xs|xs|sm|md|lg|xl|2xl|inner)\b/ },
];

function findViolations(text: string): string[] {
  const found: string[] = [];
  text.split("\n").forEach((line, index) => {
    for (const { name, pattern } of FORBIDDEN) {
      if (pattern.test(line)) found.push(`line ${index + 1}: ${name}: ${line.trim()}`);
    }
  });
  return found;
}

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return SCANNED.test(entry.name) ? [path] : [];
  });
}

/** The colour tokens from §4.2, exactly. */
const COLOUR_TOKENS: Record<string, string> = {
  page: "#FFFFFF",
  "surface-muted": "#F5F7FA",
  border: "#E2E6EC",
  "border-strong": "#C2C9D3",
  "border-control": "#848E9C",
  ink: "#10151C",
  "ink-2": "#3F4A58",
  "ink-3": "#5E6875",
  accent: "#2347D6",
  "accent-hover": "#1B38AD",
  "accent-subtle": "#EEF2FE",
  "danger-ink": "#B42318",
  "danger-bg": "#FEF2F1",
  "danger-border": "#F4B4AE",
  "danger-solid": "#C8281C",
  "outside-ink": "#8A4600",
  "outside-bg": "#FFF6E5",
  "outside-border": "#F2BD5C",
  "outside-solid": "#C77700",
  "safe-ink": "#0F6B3E",
  "safe-bg": "#ECF8F1",
  "safe-border": "#94D3AE",
  "safe-solid": "#17834D",
  "dev-ink": "#3A4656",
  "dev-bg": "#F1F3F6",
  "dev-border": "#C9D0DA",
  "user-ink": "#7A2A8C",
  "user-bg": "#F8F0FA",
  "user-border": "#E2BFEA",
};

describe("design tokens", () => {
  it("the detector catches each forbidden pattern", () => {
    const samples = [
      'style={{ color: "#fff" }}',
      "color: #10151c;",
      "background: rgb(0 0 0);",
      "color: hsl(0 0% 0%);",
      "color: oklch(0.5 0.1 200);",
      "font-family: Inter, sans-serif;",
      "style={{ fontFamily: 'Roboto' }}",
      'className="bg-blue-500 text-white"',
      'className="border-zinc-200"',
      'className="rounded-xl"',
      'className="rounded-full"',
      'className="shadow-lg"',
    ];
    for (const sample of samples) {
      expect(findViolations(sample), sample).not.toEqual([]);
    }
    const allowed = [
      'href="#main"',
      'className="bg-page text-ink border-border rounded-card shadow-popover"',
      'className="rounded-round bg-accent text-danger-ink border-l-outside-border"',
      "color: var(--color-ink);",
    ];
    for (const sample of allowed) {
      expect(findViolations(sample), sample).toEqual([]);
    }
  });

  it("no file in web/src outside tokens.css uses raw colours, fonts or default classes", () => {
    const problems = sourceFiles(SRC)
      .filter((path) => path !== TOKENS)
      .flatMap((path) =>
        findViolations(readFileSync(path, "utf8")).map((p) => `${relative(WEB, path)} ${p}`),
      );
    expect(problems).toEqual([]);
  });

  it("tokens.css clears Tailwind's built-in theme before defining the tokens", () => {
    const css = readFileSync(TOKENS, "utf8");
    for (const namespace of ["color", "font", "radius", "shadow"]) {
      expect(css).toContain(`--${namespace}-*: initial;`);
    }
  });

  it("tokens.css defines every colour token from the plan with its exact value", () => {
    const css = readFileSync(TOKENS, "utf8");
    const defined = new Map(
      [...css.matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)].map((m) => [
        m[1],
        m[2]?.toUpperCase(),
      ]),
    );
    for (const [name, hex] of Object.entries(COLOUR_TOKENS)) {
      expect(defined.get(name), `--color-${name}`).toBe(hex);
    }
  });

  it("tokens.css loads the two Atkinson Hyperlegible fonts", () => {
    const css = readFileSync(TOKENS, "utf8");
    expect(css).toContain('@import "@fontsource-variable/atkinson-hyperlegible-next"');
    expect(css).toContain('@import "@fontsource-variable/atkinson-hyperlegible-mono"');
    expect(css).toMatch(/--font-ui:\s*"Atkinson Hyperlegible Next Variable"/);
    expect(css).toMatch(/--font-mono:\s*"Atkinson Hyperlegible Mono Variable"/);
  });
});
