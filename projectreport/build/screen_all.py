"""Offline input-side coverage for the report: layers 1-2 (cleaner, rules, classifier) on every
case, with the cleaner on and off. No model call, so the LLM judge is off. The classifier uses
its committed score cache (run with SECULAYER_CLASSIFIER_DIR pointing nowhere).

Run with the project's interpreter and the HEAD source tree first on sys.path:
  python screen_all.py <headtree> <out.json>
"""
import json, re, sys
from pathlib import Path

head = Path(sys.argv[1]); out = Path(sys.argv[2])
sys.path.insert(0, str(head / "src"))

from seculayer.types import Action, LayerSwitches  # noqa: E402
from seculayer.text.unicode import decode_tags, normalize_for_matching  # noqa: E402
from seculayer_demo.config import get_settings  # noqa: E402
from seculayer_demo.console import screen_case  # noqa: E402
from seculayer_demo.scenarios import all_cases  # noqa: E402
from seculayer_demo.server.runs import make_classifier  # noqa: E402

settings = get_settings()
classifier = make_classifier(settings)
assert not classifier.model_available, "the classifier model must not load for the report"
SCORE = re.compile(r"Classifier: ([0-9.]+)")


def summarise(case, switches):
    inspections = screen_case(case.id, switches, classifier)
    cleaner, screening, rules, scores, removed_injected = [], [], set(), [], False
    withheld, blocked, unavailable = [], False, False
    inj = [normalize_for_matching(decode_tags(t) or t)[:60] for t in case.injected_text]
    for ins in inspections:
        for v in ins.verdicts:
            if v.layer.value == "hidden_text":
                cleaner.append(v.action.value)
            else:
                screening.append(v.action.value)
                for f in v.findings:
                    if f.detector.startswith("rule:"):
                        rules.add(f.detector[5:])
                for line in v.detail:
                    scores += [float(s) for s in SCORE.findall(line)]
                    if "Classifier unavailable" in line:
                        unavailable = True
        for piece in ins.hidden:
            text = normalize_for_matching(piece.text)
            if any(i and i[:40] in text for i in inj):
                removed_injected = True
        withheld += list(ins.withheld_ids)
        blocked = blocked or ins.blocked
    rank = ["off", "passed", "flagged", "withheld", "blocked"]
    screen_overall = max(screening, key=lambda a: rank.index(a) if a in rank else 0)
    return {
        "cleaner": "removed" if "removed" in cleaner else (cleaner[0] if cleaner else "off"),
        "cleaner_removed_injected": removed_injected,
        "screening": screen_overall,
        "rules": sorted(rules),
        "classifier_max": max(scores) if scores else None,
        "classifier_unavailable": unavailable,
        "withheld": withheld,
        "blocked": blocked,
    }


rows = []
for case in all_cases():
    row = {"id": case.id, "scenario": case.scenario_id, "kind": case.kind, "title": case.title,
           "primary": case.is_primary, "hard_case": case.hard_case}
    row["cleaner_on"] = summarise(case, LayerSwitches())
    row["cleaner_off"] = summarise(case, LayerSwitches(hidden_text=False))
    row["rules_only_cleaner_on"] = summarise(case, LayerSwitches(classifier=False))
    row["classifier_only_cleaner_on"] = summarise(case, LayerSwitches(rules=False))
    rows.append(row)
    c = row["cleaner_on"]
    print(f'{case.id:42} {case.kind:6} cleaner={c["cleaner"]:8} inj={int(c["cleaner_removed_injected"])} '
          f'screen={c["screening"]:8} rules={",".join(c["rules"]) or "-"} clf={c["classifier_max"]} '
          f'| off: screen={row["cleaner_off"]["screening"]} rules={",".join(row["cleaner_off"]["rules"]) or "-"} clf={row["cleaner_off"]["classifier_max"]}')
out.write_text(json.dumps(rows, indent=1))
print(len(rows), "cases")
