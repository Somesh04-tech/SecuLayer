# SecuLayer build progress
Plan: docs/PLAN.md · Last updated: 2026-10-23, session 2

## Milestones
| ID | Name | Status (not started / in progress / done) | Verified by | Commit |
|----|------|-------------------------------------------|-------------|--------|
| M1 | Foundation | done | make check (43 pytest, 20 Vitest), make e2e (8 Playwright tests), screenshots m1-*.png reviewed, run.sh curl checks, doctor, storage check | see `git log` ("M1: foundation …") |
| M2 | SecuLayer core and scenario data | done, except the committed classifier score cache (see Known issues) | make check (unit tests for every layer, data validation), `seculayer screen --case inbox.hidden_forward` with and without the cleaner | see `git log` ("M2: SecuLayer layers, …") |
| M3 | Model gateway, toy apps and run API | in progress: all code and tests done; the first recordings and `doctor --online` need OPENAI_API_KEY | make check (371 pytest, 20 Vitest, lint, typecheck), make e2e (8 Playwright tests), make types | see `git log` ("M3: model gateway, …") |
| M4 | Attack Lab, part 1 (run both ways) | not started | | |
| M5 | Attack Lab, part 2 (show the mechanism) | not started | | |
| M6 | Attack qualification and full recordings | not started | | |
| M7 | Evaluation and Results page | not started | | |
| M8 | Explainer pages and Sandbox | not started | | |
| M9 | Accessibility, presenter readiness and polish | not started | | |
| M10 | Final verification | not started | | |

## Current state
Session 2 ran in a Claude Code cloud container (Linux, Python 3.12, Node 22.22), not on the laptop. It had no OPENAI_API_KEY, and the proxy refused the classifier download (403 from the Hugging Face CDN). Everything that needs neither was built and tested.

**The library (`src/seculayer`) is complete** (§6.5):
- `engine.py`: the `SecuLayer` class with `inspect` (layers 1–2), `harden` (3), `review_tool_call` (4), `review_tool_arguments` and `review_output` (5). It also supports `observe_only`.
- `layers/`: `hidden_text.py`, `screening.py`, `rules.py`, `hardening.py` (with the exact §6.7 trust policy), `tool_guard.py` and `output_guard.py`.
- `detect/judge.py`: the exact judge prompts, the strict schema, derived IDs, and parsing with the "judge unavailable" fallback.
- The public API is in `__init__.py`. mypy strict passes.

**Scenario data is complete** (§5):
- `data/scenarios/{support,inbox,page,helpdesk}.toml` hold 12 attacks × 3 (36 attack cases) and 20 normal-use cases.
- Content: 13 page fixtures, 17 knowledge-base articles and the inbox emails, all using `.example` domains and the invisible-character markers.
- The loader (`scenarios.py`) validates the data, and `checks.py` holds the success and utility checks.

**The demo backend (M3)**:
- `gateway/`: canonical requests and keys, the recording store (`data/recordings/{model}/{scenario}.jsonl.gz`), the replay, live and record modes, `ReplayMiss`, the trial-1 fallback, budget checks with `data/spend.jsonl`, pricing, the OpenAI transport (60 s timeout, 2 retries) and `FakeModel`.
- `apps/`: the four toy apps exactly as §5.3–5.6, the mock mail tools, BM25 retrieval and the naive renderer (attacker events).
- `judge_openai.py`: the judge through the gateway, with Pydantic validation.
- `runner.py`: `AgentRunner`, a generator that streams the §6.9 events and pauses for confirmation. It also holds the outcome, banner and stopped-by logic. `anatomy.py` builds the source-coloured prompt parts.
- `server/`: `events.py` (the Pydantic event union), `runs.py` (run service, paused-run store with a 10-minute TTL, classifier pre-warm) and `routes.py`. The routes are `GET /api/scenarios`, `GET /api/scenarios/{id}`, `POST /api/runs` (NDJSON), `POST /api/runs/{id}/decision`, `POST /api/screen`, `GET /api/eval/latest` (a 404 until M7) and `GET /api/schema/run-event`.
- CLI:
  - `screen`, `run`, `record` and `export-openapi`;
  - `doctor --online`, which checks function calling and structured output;
  - `warm-classifier`, which fills `data/cache/classifier_scores.jsonl`.
- `make types` writes `web/src/api/openapi.json` and `web/src/api/types.gen.ts`, and works with TypeScript 6. `make record` defaults to the two featured cases with configurations A and B.

**Tests**: 371 pytest pass (3 classifier tests skip because the model is absent). They cover:
- every hidden-HTML pattern, every rule on its payloads and baits, Base64 rescans, hardening, every tool-guard path and the output-guard cases;
- data validation;
- the gateway modes;
- runner tests with FakeModel: the tool loop, a blocked call halting, confirmation both ways, output redaction, ReplayMiss, determinism and event validation;
- API tests: a streamed replay run, `/decision` and `/api/screen`;
- the secret scan.

**How to demo it right now**: `uv run seculayer screen --case inbox.hidden_forward` (add `--layers=-hidden_text` to see screening withhold the email). `uv run seculayer run --case inbox.hidden_forward --protected` reports "not recorded" until recordings exist.

## Measured facts
- Attack qualification: not run yet (M6).
- API tokens used so far: 0 of SECULAYER_TOKEN_BUDGET (1,500,000).
- Rules without the classifier or judge, measured with `seculayer screen` on every case (cleaner on / off):
  - **Caught by the cleaner** (with the cleaner off, the rules withhold the item instead): hidden_forward (+ comment variant), hidden_link (all 3), image_exfil (+ link variant).
  - **Withheld by the rules either way**:
    - hidden_forward visible variant;
    - fake_system (all 3);
    - image_exfil alt-text variant;
    - poisoned_phish and its mid-article variant;
    - link_exfil (all 3).
  - **Blocked by the rules** (user message): support.override and its "repeat" variant.
  - **Flagged only**: support.roleplay and its developer-mode variant.
  - **Removed by the cleaner only** (the rules see nothing with the cleaner off): tag_smuggling and its zero-width variant.
  - **No rule match**, as the plan predicts:
    - support.override Spanish variant;
    - support.roleplay grandma variant;
    - support.obfuscate (all 3: the decoded Base64 needs the classifier);
    - polite_invoice (all 3);
    - poisoned_phish "policy" variant;
    - misinformation (all 3);
    - tag_smuggling visible control.
  - Normal-use bait: no rule false alarms, except page.n_security_blog. That page quotes an override in visible text, so the rules withhold it: a known false alarm, asserted in `tests/unit/test_rules.py`.
- Timings in the cloud container: `make check` 19 s; `make e2e` 26 s for the tests.

## Decisions and deviations from the plan
- 2026-10-23 (session 2): added the planned M2 extensions:
  - `Source.SECULAYER`, for the policy and withheld placeholders;
  - `Segment.outside_scaffold`, for app text that frames outside content ("URL: … Page HTML:", "Knowledge-base articles:"), which hardening moves with that content;
  - `Segment.meta`, for an email's From and Subject;
  - `Message.content`, for model-written text (assistant replies, tool-call arguments);
  - `RunContext.developer_text` and `visible_outside`;
  - `Policy.user_name` and `Policy.protected_labels`, so copy never repeats a secret;
  - `ScreeningPolicy.judge_user`: true only for the support chat;
  - `JudgeUnavailable`.
- 2026-10-23: derived IDs (spotlighting markers, judge item IDs, mock message IDs) come from a SHA-256 of the case ID and the purpose, not the trial. The trial is part of the recording key, so trials share identical prompts. That is what makes "a variant recorded once falls back to trial 1" work.
- 2026-10-23: the judge is called with `responses.create` and an explicit strict `json_schema` text format, then validated with the Pydantic `JudgeOutput` model. On the wire this is the same request `responses.parse(text_format=…)` sends, but it keeps every request a plain dict that canonicalises and records the same way. The judge's `max_output_tokens` is 2,000, because it reasons at effort `low`.
- 2026-10-23: screening rows whose items were only flagged use the `flagged` action. §4.2 has no chip for it, so M4 should style it like Passed.
- 2026-10-23: the output guard checks the canary first, then images and links, then protected values in what's left. Private data inside an image or link address therefore removes that address ("removes any link whose address contains private data", §5.7) instead of withholding the whole reply. Protected values anywhere else still withhold the reply.
- 2026-10-23: on outbound tool arguments, the output guard checks only the canary. Protected values in arguments belong to the tool guard's data check (confirm). Otherwise the polite invoice would be blocked outright, which contradicts the plan's honest-limit narrative.
- 2026-10-23: `clean_html` escapes tags that aren't HTML before parsing. Without this, `html.parser` silently dropped a stray `</email>`, hiding the attacker's fake marker from the text the model reads (a test caught it).
- 2026-10-23: BM25 uses a light plural stemmer and splits hyphenated words. The fake-policy articles (`home-office-2026*.md`) gained one attacker sentence: "This covers desks, chairs, monitors and other equipment." Without it, the plan's article shares no words with "Can I expense a new desk and monitor?" and is never retrieved. This is the kind of wording a real attacker uses to match questions, within the §5.9 realism budget.
- 2026-10-23: the event schema extends §6.9 in these ways:
  - `layer.verdict.detail` (sub-check lines);
  - `run.started.layers`;
  - `model.response.trial`;
  - `run.paused.dialog.reason`;
  - `tool.decision` actions `approved` and `declined`;
  - an anatomy part source `model` (assistant text) and a part flag `removed` (hidden text SecuLayer removed);
  - `stopped_by` names a layer.
  - Banner sentences start in lowercase, so the UI renders "{title}: {sentence}".
- 2026-10-23: `stopped_by` credits the layer that stopped the harmful action (tool guard or output guard) when one did. Otherwise it credits the first input-side layer that removed, withheld or blocked the attacker's text. The cleaner counts only when the text it removed contains the case's injected text.
- 2026-10-23: replay pacing (events 150 ms apart, §3.4) is left to the client in M4, so the server streams at once and tests stay fast. In replay and record modes, events before the first app model call are held until it returns, so `run.started` can report `trials_available`.
- 2026-10-23: a layer that only decides never changes a model request, but a blocked call ends the run, so later requests are never made. For each protected configuration in the inbox, `seculayer record` also runs a companion with the tool guard off, which records the continuation. `--configs combos` records every Layers-menu combination at trial 1.
- 2026-10-23: the security-blog fixture's quoted address uses `invoice-mirror.example`, not `example.net`: every domain stays under `.example`.
- 2026-10-23: CLAUDE.md says "don't push; there is no remote". This cloud session has a GitHub remote, and its task instructions say to push to `claude/relaxed-pasteur-aytywd`, so the commits were pushed there. Nothing else changed.

## Known issues
- **No recordings yet.** M3 step 6 and the acceptance check `env -u OPENAI_API_KEY uv run seculayer run --case inbox.hidden_forward --protected --mode replay` need real recordings. Making them needs the developer's key; until then that command ends with "This combination of layers wasn't recorded". Recordings are never fabricated.
- **`doctor --online` hasn't been run against the real API.** Run it before recording and note anything it rejects (for example `reasoning.effort: none` or `parallel_tool_calls` on the pinned snapshots).
- **`data/cache/classifier_scores.jsonl` doesn't exist yet**, because the classifier couldn't be downloaded in the cloud container. Run `uv run seculayer fetch-model && uv run seculayer warm-classifier` on the laptop, then commit the file. Until then, screening shows "Classifier unavailable (model not downloaded)" and the classifier-only catches are missing: support.obfuscate and the planned 0.999 false alarm on support.n_instructions.
- In the cloud container, `make e2e` needed a Playwright browsers folder that links build 1248 to the preinstalled 1243. On the laptop, `.cache/ms-playwright` already has 1248.
- The Playwright web server now runs `uv run --frozen`. Without `--frozen`, uv rewrote `uv.lock`'s `exclude-newer` timestamp in a different timezone.
- Carried over from M1: in the Home diagram, the "One model" and "Reply and actions" nodes look a little like buttons (revisit in M4); eslint 9.39.5 is deprecated (kept for jsx-a11y).

## Next step
On the laptop, with OPENAI_API_KEY in `.env`:
1. Run `uv run seculayer doctor --online`. Fix and record anything the API rejects.
2. Run `uv run seculayer fetch-model && uv run seculayer warm-classifier`, then commit `data/cache/classifier_scores.jsonl`.
3. Run `uv run seculayer record --cases inbox.hidden_forward,support.override --configs A,B,combos --trials 3`. The command prints its token estimate and asks before starting (about 40–80 real calls once the layer combinations deduplicate).
4. Check that `env -u OPENAI_API_KEY uv run seculayer run --case inbox.hidden_forward --protected --mode replay` completes, record the token use here, mark M3 done and commit "M3: first recordings".
5. Then continue with M4 (the Attack Lab UI), using `web/src/api/types.gen.ts` and `POST /api/runs`.
