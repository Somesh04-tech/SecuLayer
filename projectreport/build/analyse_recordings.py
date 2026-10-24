"""Summarise the committed recordings (git HEAD) for the report: one row per recorded model call.

Reads data/recordings/*/*.jsonl.gz from HEAD through `git show`, so in-progress edits in the
working tree never leak into the report. Writes projectreport/build/data/recordings_summary.json.
Usage: python analyse_recordings.py <repo-root>
"""
import gzip, io, json, subprocess, sys
from pathlib import Path

repo = Path(sys.argv[1])
files = subprocess.run(["git", "-C", str(repo), "ls-files", "data/recordings"], capture_output=True, text=True, check=True).stdout.split()
head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
rows = []
for f in files:
    raw = subprocess.run(["git", "-C", str(repo), "show", f"HEAD:{f}"], capture_output=True, check=True).stdout
    for line in gzip.GzipFile(fileobj=io.BytesIO(raw)).read().decode("utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        resp = r.get("response", {})
        out_text, calls = [], []
        for item in resp.get("output", []) or []:
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        out_text.append(c.get("text", ""))
            elif item.get("type") == "function_call":
                calls.append({"name": item.get("name"), "arguments": item.get("arguments")})
        usage = resp.get("usage") or {}
        rows.append({
            "file": f, "case_id": r.get("case_id"), "purpose": r.get("purpose"), "trial": r.get("trial"),
            "extra": r.get("extra"), "latency_ms": r.get("latency_ms"), "model": r.get("model"),
            "recorded_at": r.get("recorded_at"),
            "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "n_input_items": len(r.get("request", {}).get("input", []) or []),
            "has_tools": bool(r.get("request", {}).get("tools")),
            "instructions_has_policy": "Security policy (added by SecuLayer)" in json.dumps(r.get("request", {})),
            "output_text": "\n".join(out_text), "tool_calls": calls,
            "keys": sorted(r.keys()),
        })
out = repo / "projectreport/build/data/recordings_summary.json"
out.write_text(json.dumps({"head": head, "rows": rows}, indent=1, ensure_ascii=False))
print("HEAD", head, "rows", len(rows))
for row in rows:
    print(row["case_id"], row["purpose"], "trial", row["trial"], "extra", row["extra"], f'{row["latency_ms"]} ms', row["input_tokens"], row["output_tokens"], "policy" if row["instructions_has_policy"] else "naive", [c["name"] for c in row["tool_calls"]], repr(row["output_text"][:90]))
