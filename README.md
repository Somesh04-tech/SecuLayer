# SecuLayer

SecuLayer is a local web app that teaches prompt injection. It shows small sandboxed AI apps
getting hijacked by injected instructions, then shows a layered defense module stopping the
same attacks and explaining which check caught each one and why.

This README is a stub. The full version (how to run it, the two modes, how the results were
measured, limits and credits) is written in milestone M10. The plan is `docs/PLAN.md`.

## Quick start

```sh
./run.sh            # replay mode at http://127.0.0.1:8765
./run.sh --no-open  # same, without opening the browser
uv run seculayer doctor
```

Everything here is a sandbox with fake data. Nothing leaves this computer.
