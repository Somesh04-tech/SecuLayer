#!/usr/bin/env bash
# Offline replays of the committed (HEAD) recordings for the report. No API key, no network, and
# the classifier runs from its committed score cache (SECULAYER_CLASSIFIER_DIR points nowhere).
# Usage: run_replays.sh <repo> <headtree> <out-dir>
#   <headtree> is `git archive HEAD src data models/manifest.toml pyproject.toml` extracted, so the
#   main session's in-progress payload edits in the working tree can't change these results.
set -u
R="$1"; H="$2"; OUT="$3"
mkdir -p "$OUT"
run() {  # name, then CLI args
  local name="$1"; shift
  (cd "$H" && env -u OPENAI_API_KEY SECULAYER_CLASSIFIER_DIR=/nonexistent-classifier \
    "$R/.venv/bin/python" -c "import sys; sys.path.insert(0, '$H/src'); from seculayer_demo.cli import app; sys.argv=['seculayer', *sys.argv[1:]]; app()" "$@" \
    > "$OUT/$name.txt" 2>&1; echo "exit=$?" >> "$OUT/$name.txt")
  echo "$name: $(grep -m1 '^■' "$OUT/$name.txt")"
}
for t in 1 2 3; do
  run "A_inbox.hidden_forward_t$t" run --case inbox.hidden_forward --mode replay --trial $t
  run "B_inbox.hidden_forward_t$t" run --case inbox.hidden_forward --protected --mode replay --trial $t
  run "Bnotg_inbox.hidden_forward_t$t" run --case inbox.hidden_forward --protected --layers=-tool_guard --mode replay --trial $t
  run "A_support.override_t$t" run --case support.override --mode replay --trial $t
  run "B_support.override_t$t" run --case support.override --protected --mode replay --trial $t
done
run "Bnocleaner_inbox.hidden_forward_t1" run --case inbox.hidden_forward --protected --layers=-hidden_text --mode replay --trial 1
