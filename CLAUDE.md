# SecuLayer
Educational demo of prompt injection and a layered defense. The plan is docs/PLAN.md.
Progress is in PROGRESS.md: read it first, and update and commit it at the end of every session.

## Commands
- ./run.sh (replay mode, http://127.0.0.1:8765) · ./run.sh --live
- make setup · make check · make e2e · make eval · make record · make replay-check · make dev · make types
- uv run seculayer doctor

## Conventions
- src/seculayer is the reusable library: it never imports seculayer_demo, fastapi or openai (tests/test_architecture.py).
- Colours, fonts, radii and spacing come only from web/src/styles/tokens.css: no raw colour values or default Tailwind palette classes (web/tests/design-tokens.test.ts). Check new screens against the avoid-list in docs/PLAN.md §4.7.
- UI copy: plain language, sentence case, glossary terms wrapped in <Term>, every rate with its denominator.
- Fake data uses .example domains only. The only network calls are to the OpenAI API (live, record, eval-live) and the pinned classifier download; tests block everything else.
- Never print, log or record OPENAI_API_KEY. Recordings change only through make record / make eval-live.
- Tests check behaviour. Don't weaken, skip or delete a test to make it pass, and don't special-case test inputs.
- Everything heavy stays on the external drive (docs/PLAN.md §8.5). The repository lives there, and .claude/settings.json points the uv, npm and Playwright caches at .cache/. Never install into ~/.cache or ~/.npm.
- The OpenAI key is on a free tier: no API calls in tests or development (use recordings or FakeModel). Only the recording steps in the plan call the API, within SECULAYER_TOKEN_BUDGET.
- Keep the laptop responsive: one Playwright worker, at most two Vitest threads, and the full e2e suite only at the end of a milestone.
- Commit at the end of each milestone, with the message "M<n>: <summary>". Don't push; there is no remote.
