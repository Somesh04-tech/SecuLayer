"""Per-layer processing time of SecuLayer's local checks, measured by replaying the committed
recordings of the two featured cases with SecuLayer on (configuration B). Model and judge calls
come from recordings; the classifier answers from its committed score cache, so its time here
is a cache lookup, not inference. Usage: python layer_latency.py <headtree> <out.json> [repeats]
"""
import json, statistics, sys
from pathlib import Path

head = Path(sys.argv[1]); out = Path(sys.argv[2]); repeats = int(sys.argv[3]) if len(sys.argv) > 3 else 5
sys.path.insert(0, str(head / "src"))
from seculayer.types import LayerSwitches  # noqa: E402
from seculayer_demo.config import get_settings  # noqa: E402
from seculayer_demo.gateway import ModelGateway, RecordingStore  # noqa: E402
from seculayer_demo.runner import AgentRunner, RunRequest  # noqa: E402
from seculayer_demo.server.runs import make_classifier  # noqa: E402

settings = get_settings()
classifier = make_classifier(settings)
assert not classifier.model_available
store = RecordingStore(settings.recordings_dir)
rows = []
for case in ("inbox.hidden_forward", "support.override"):
    for trial in (1, 2, 3):
        for rep in range(repeats):
            gateway = ModelGateway("replay", store)
            runner = AgentRunner(RunRequest(case, True, settings.model, LayerSwitches(), trial),
                                 gateway=gateway, judge_model=settings.judge_model,
                                 classifier=classifier, run_id=f"lat-{case}-{trial}-{rep}")
            for event in runner.events():
                data = event.model_dump(mode="json")
                if data["type"] == "layer.verdict":
                    rows.append({"case": case, "trial": trial, "rep": rep, "layer": data["layer"],
                                 "step": data["step"], "action": data["action"], "latency_ms": data["latency_ms"]})
summary = {}
for case in ("inbox.hidden_forward", "support.override"):
    for layer in ("hidden_text", "screening", "hardening", "tool_guard", "output_guard"):
        vals = [r["latency_ms"] for r in rows if r["case"] == case and r["layer"] == layer and r["action"] not in ("not_reached", "off")]
        if vals:
            summary[f"{case}|{layer}"] = {"n": len(vals), "median_ms": statistics.median(vals), "max_ms": max(vals)}
out.write_text(json.dumps({"rows": rows, "summary": summary}, indent=1))
for k, v in summary.items():
    print(k, v)
