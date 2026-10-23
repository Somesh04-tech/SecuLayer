# SecuLayer build progress
Plan: docs/PLAN.md · Last updated: 2026-10-23, session 1

## Milestones
| ID | Name | Status (not started / in progress / done) | Verified by | Commit |
|----|------|-------------------------------------------|-------------|--------|
| M1 | Foundation | done | make check (43 pytest, 20 Vitest), make e2e (8 Playwright tests), screenshots m1-*.png reviewed, run.sh curl checks, doctor, storage check | see `git log` ("M1: foundation …") |
| M2 | SecuLayer core and scenario data | in progress (uncommitted) | | |
| M3 | Model gateway, toy apps and run API | not started | | |
| M4 | Attack Lab, part 1 (run both ways) | not started | | |
| M5 | Attack Lab, part 2 (show the mechanism) | not started | | |
| M6 | Attack qualification and full recordings | not started | | |
| M7 | Evaluation and Results page | not started | | |
| M8 | Explainer pages and Sandbox | not started | | |
| M9 | Accessibility, presenter readiness and polish | not started | | |
| M10 | Final verification | not started | | |

## Current state
M1 is done. The app shell starts with one command and every test layer is wired up.
- `./run.sh` installs missing dependencies, rebuilds `web/dist` only when it's stale, and serves the app at http://127.0.0.1:8765 in replay mode. The `--no-open` flag skips opening the browser.
- The backend (`src/seculayer_demo`) has the FastAPI app factory, `/api/health`, `/api/meta` (mode, live availability, models, classifier presence, recordings, budget, version), the §6.10 security headers as pure ASGI middleware (streaming-safe), and the SPA fallback (unknown `/api/*` paths return a JSON 404; path traversal out of `dist` is refused). The CLI has `serve` (loopback only; live mode needs a key) and `doctor`.
- `src/seculayer` is an empty library package, guarded by `tests/test_architecture.py`.
- The frontend has `tokens.css` (the Tailwind theme reset plus every §4.2–4.4 token), self-hosted Atkinson fonts, the AppShell (TopBar, nav, ModeIndicator popover, TextSizeToggle, skip link, footer), a designed empty state on every §3.2 route, the not-found page and the server-unreachable state.
- Tests:
  - pytest: socket guard, config, server, CSP, SPA fallback, doctor, architecture.
  - Vitest: AppShell, design tokens.
  - Playwright `e2e/shell.spec.ts`: white body, loaded font, no pill shapes, axe, local-only requests, every route, mode popover, keyboard order.
- Screenshot review (M1), checking `artifacts/screenshots/m1-home-1440.png`, `m1-home-1280.png` and `m1-home-1280-large.png` against §4 and §4.7. All of these hold:
  - the page is pure white;
  - Atkinson Next is used for the UI and Atkinson Mono only for prompt text;
  - there are no gradients, pill buttons, eyebrow labels, centred hero, shadows on cards or default fonts;
  - bordered containers go two levels deep at most;
  - the source tints match the tokens;
  - large-text mode holds at 1280×720 with no horizontal scroll.
  
  No new avoid-list entries were needed.

## Measured facts
- Attack qualification: not run yet (M6).
- API tokens used so far: 0 of SECULAYER_TOKEN_BUDGET (1,500,000).
- Internal disk free at the start of M1: 4,307,152,896 bytes (`df -B1 /`, 2026-10-23 22:39 IST). At the end of M1: 4,279,422,976 bytes, so it went down by 27 MB (limit about 50 MB).
- Sizes on the drive: `.venv` 277 MB, `web/node_modules` 311 MB, `.cache/ms-playwright` 278 MB (chromium_headless_shell-1248), `.cache/npm` 563 MB.
- Timings on this laptop: `make check` about 32 s; `make e2e` (build plus 8 tests) about 60 s; first `uv sync` 90 s; first `npm install` about 3 min.

## Decisions and deviations from the plan
- 2026-10-23: the classifier runs with 2 onnxruntime threads, not the plan's 4: 2 measured fastest on this 2-core laptop (17 ms median for a short input, 574 ms for a 512-token window, 1.9 s to load). `LICENSE` and `NOTICE` exist at the pinned revision, and their hashes are in `models/manifest.toml`. Downloads are redirected to `us.aws.cdn.hf.co` and to `huggingface.co/api/resolve-cache`; only HTTPS to huggingface.co, *.huggingface.co and *.hf.co is allowed.
- 2026-10-23: openapi-typescript 7.13.0 declares a `typescript ^5` peer dependency, which conflicts with the pinned TypeScript 6.0.3. `web/package.json` uses an npm `overrides` entry that points it at the project's TypeScript, rather than `--legacy-peer-deps`. Check that `make types` works on TS 6 in M3.
- 2026-10-23: the mode popover can't switch modes at runtime yet. §3.2 says it "offers to switch" when a key is configured, but §6.9 has no endpoint for that. For now the switch is disabled and the popover tells the viewer to restart with `./run.sh --live`. Decide in M3/M4 whether to add a runtime switch (for example `POST /api/mode`) or keep the restart.
- 2026-10-23: the `Popover` component focuses its panel on open, not its first focusable child. Otherwise a `Term` inside gets focus, opens its tooltip, and swallows the first Escape (an e2e test caught this).
- 2026-10-23: Makefile targets for later milestones print "not implemented yet (M<n>)" and their recipes exit 1. `make` itself then reports exit status 2, which is how make always reports a failed recipe.
- 2026-10-23: `seculayer doctor` lives in `src/seculayer_demo/doctor.py`, with shared read-only facts in `status.py`, so it can be tested. `cli.py` stays thin. Classifier hash checks arrive with `fetch-model` in M2.
- 2026-10-23: M1 was built with two agents: a forked agent wrote `web/` while the main session wrote the backend, tests, Makefile and run.sh. Only one of them ran heavy installs or test suites at a time.

## Known issues
- In the Home diagram, the "One model" and "Reply and actions" nodes are bordered boxes that look a little like buttons. Revisit them when Home reaches its near-final form in M4.
- npm reports eslint 9.39.5 as deprecated. The plan keeps ESLint 9 deliberately, because jsx-a11y supports only up to 9.

## Next step
Finish M2. The session stopped at the usage limit; nothing from M2 is committed yet.
- Done:
  - `src/seculayer/types.py` and `policy.py`;
  - `text/unicode.py`, `encodings.py`, `urls.py` and `html.py` (all sanity-checked by hand; no unit tests yet);
  - `layers/rules.py` (written, untested);
  - the classifier (`detect/prompt_guard.py`, `fetch_model.py`, `models/manifest.toml`, 29 tests passing). The model is downloaded and hash-checked.
- Partial: the scenario-data agent was stopped mid-way. Check what exists under `data/scenarios`, `data/content`, `src/seculayer_demo/{scenarios.py,checks.py,apps/}` and `tests/unit/test_{scenarios,checks,apps}.py`, then finish them.
- To do:
  - `layers/hidden_text.py`, `screening.py`, `hardening.py`, `tool_guard.py`, `output_guard.py`;
  - `detect/judge.py` (protocol, the exact §6.7 prompts, schema, ID helpers);
  - `engine.py` (the SecuLayer class) and the public API in `__init__.py`;
  - the `seculayer screen` command;
  - unit tests for every layer (§9 M2 acceptance);
  - populating and committing `data/cache/classifier_scores.jsonl`.
- Planned additions (record them as deviations once made):
  - `Source.SECULAYER` for the markers and policy that hardening adds;
  - `ScreeningPolicy.judge_user` (only the support chat sends the user's message to the judge);
  - a `Policy.user_name` key ("Dana" / "the customer");
  - optional labels for protected values, so withheld-reply copy never repeats the secret;
  - `RunContext` fields for developer text and the visible outside text (used by the output guard's link rule).
- Lint to fix: E501 at `policy.py:58`, and RUF036 at `html.py:71` and `html.py:115`.
M2: SecuLayer core and scenario data (docs/PLAN.md §9 M2; read §5, §6.1–6.7 and §8.1's classifier files first).
