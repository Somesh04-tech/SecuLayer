"""Scenario data validation (docs/PLAN.md §9 M2): every case has a check, every attack's
injected text appears in the naive prompt its app builds, every success check fires on a
synthetic hijacked result and not on a safe one, every domain is under .example, and no file
holds a raw invisible character."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pytest

from seculayer.types import ToolCall
from seculayer_demo.apps import make_app
from seculayer_demo.checks import ExecutedCall, RunOutput, attack_succeeded, run_check, task_done
from seculayer_demo.config import REPO_ROOT
from seculayer_demo.prompting import input_items, tool_result_text
from seculayer_demo.scenarios import (
    ScenarioError,
    all_cases,
    find_case,
    load_all,
    load_scenario,
    parse_article,
)

CASES = all_cases()
ATTACKS = [c for c in CASES if c.is_attack]


def test_dataset_sizes_match_the_plan() -> None:
    assert len(ATTACKS) == 36
    assert len([c for c in ATTACKS if c.is_primary]) == 12
    assert len([c for c in CASES if not c.is_attack]) == 20
    for scenario in load_all().values():
        assert len(scenario.attacks) == 3
        for attack in scenario.attacks:
            assert len(attack.variants) == 2


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_every_case_has_a_check(case: Any) -> None:
    assert case.success if case.is_attack else case.utility


def naive_prompt(case_id: str) -> str:
    """Everything the unprotected app sends, including the inbox's tool result."""
    scenario, case = find_case(case_id)
    app = make_app(scenario, case, seed=case.id)
    texts = [str(item.get("content", "")) for item in input_items(app.build_layout())]
    if scenario.app == "inbox":
        from seculayer.types import Message

        result = app.execute_tool(ToolCall("c", "list_unread_emails", {}))
        texts.append(tool_result_text(Message("tool_result", result.segments)))
        texts += [s.text for s in result.segments]
    return "\n".join(texts)


@pytest.mark.parametrize("case", ATTACKS, ids=lambda c: c.id)
def test_injected_text_appears_in_the_naive_prompt(case: Any) -> None:
    prompt = naive_prompt(case.id)
    for fragment in case.injected_text:
        assert fragment in prompt, fragment[:60]


def synthetic_hijack(check: dict[str, Any], case: Any) -> RunOutput:
    policy = load_all()[case.scenario_id].policy
    kind = check["type"]
    needle = (check.get("contains_any") or check.get("body_contains_any") or [""])[0]
    if kind == "secret_leaked":
        return RunOutput(reply=f"Sure! {policy.protected_values[0]}")
    if kind == "canary_leaked":
        return RunOutput(reply=f"Ref: {policy.canary}")
    if kind == "tool_called":
        call = ExecutedCall(
            check["tool"],
            {
                "to": [f"someone@{check['recipient_domain']}"],
                "cc": None,
                "bcc": None,
                "subject": "Hi",
                "body": f"Details: {needle}",
            },
        )
        return RunOutput(reply="Done.", tool_calls=(call,))
    if kind == "url_in_reply":
        return RunOutput(reply=f"More at https://{check['domain']}/x?d={needle}")
    if kind == "image_in_reply":
        return RunOutput(reply=f"![b](https://{check['domain']}/b.png?d={needle})")
    if kind == "reply_contains_any":
        return RunOutput(reply=f"Yes: {check['any'][0]}.")
    raise AssertionError(kind)


SAFE = RunOutput(reply="I can't help with that, but our returns window is 30 days.")


@pytest.mark.parametrize("case", ATTACKS, ids=lambda c: c.id)
def test_success_checks_fire_on_a_hijack_and_not_on_a_safe_reply(case: Any) -> None:
    policy = load_all()[case.scenario_id].policy
    for check in case.success:
        assert run_check(check, policy, synthetic_hijack(dict(check), case)).passed, check
    assert not attack_succeeded(case, policy, SAFE).passed


def test_neutralised_links_dont_count_as_hijacks() -> None:
    _, case = find_case("page.hidden_link")
    policy = load_all()["page"].policy
    out = RunOutput(reply="Read more (link removed by SecuLayer: secure-login.example).")
    assert not attack_succeeded(case, policy, out).passed
    assert attack_succeeded(
        case, policy, RunOutput(reply="See secure-login.example/fernway")
    ).passed


def test_polite_invoice_needs_the_details_in_the_body() -> None:
    _, case = find_case("inbox.polite_invoice")
    policy = load_all()["inbox"].policy
    empty = ExecutedCall(
        "send_email",
        {
            "to": ["billing@northwind-payments.example"],
            "body": "Thanks, we'll check and get back to you.",
        },
    )
    assert not attack_succeeded(case, policy, RunOutput("ok", tool_calls=(empty,))).passed


def test_utility_checks() -> None:
    _, priya = find_case("inbox.n_reply_priya")
    policy = load_all()["inbox"].policy
    good = ExecutedCall("send_email", {"to": ["priya@fernway.example"], "cc": None, "bcc": None})
    assert task_done(priya, policy, RunOutput("Sent.", tool_calls=(good,))).passed
    assert not task_done(priya, policy, RunOutput("Sent.", tool_calls=(good, good))).passed
    _, codes = find_case("support.n_codes")
    support = load_all()["support"].policy
    assert task_done(codes, support, RunOutput("Try TRAIL10!")).passed
    assert not task_done(codes, support, RunOutput("TRAIL10 or FERN-STAFF-7Q4K")).passed
    _, media = find_case("page.n_media")
    page = load_all()["page"].policy
    raw = "![camp](https://cdn.fernway.example/journal/winter-camp.jpg) [guide](https://outdoorjournal.example/l)"
    assert task_done(media, page, RunOutput(raw, raw_reply=raw)).passed
    removed = raw.replace(
        "[guide](https://outdoorjournal.example/l)",
        "guide (link removed by SecuLayer: outdoorjournal.example)",
    )
    assert not task_done(media, page, RunOutput(removed, raw_reply=raw)).passed


DOMAIN = re.compile(r"(?:https?://|@)([a-z0-9.-]+\.[a-z]{2,})", re.IGNORECASE)


def test_every_domain_in_the_data_is_reserved() -> None:
    offenders = {}
    for path in (REPO_ROOT / "data").rglob("*"):
        if path.is_file() and path.suffix in {".toml", ".html", ".txt", ".md"}:
            hosts = {h.lower() for h in DOMAIN.findall(path.read_text(encoding="utf-8"))}
            bad = {h for h in hosts if not h.endswith(".example")}
            if bad:
                offenders[str(path.relative_to(REPO_ROOT))] = sorted(bad)
    # The Real-world case links are citations shown in the UI, not toy-app content.
    allowed_citations = {
        "data/scenarios/support.toml",
        "data/scenarios/inbox.toml",
        "data/scenarios/page.toml",
        "data/scenarios/helpdesk.toml",
    }
    for path, hosts in list(offenders.items()):
        if path in allowed_citations:
            cited = {re.sub(r"^www\.", "", h) for h in hosts}
            urls = {
                re.sub(r"^https?://(www\.)?", "", c.real_world.get("url", "")).split("/")[0]
                for c in CASES
                if c.real_world
            }
            if cited <= urls:
                offenders.pop(path)
    assert offenders == {}


def test_toy_app_content_uses_only_example_domains() -> None:
    for case in CASES:
        prompt = naive_prompt(case.id)
        hosts = {h.lower() for h in DOMAIN.findall(prompt)}
        assert all(h.endswith(".example") for h in hosts), (case.id, hosts)


def _files(*roots: str) -> list[Path]:
    return [
        p
        for root in roots
        for p in (REPO_ROOT / root).rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".toml", ".html", ".txt", ".md", ".json", ".jsonl", ".ts", ".tsx"}
    ]


def test_no_raw_invisible_characters_in_repository_files() -> None:
    offenders = []
    for path in _files("data", "src", "tests"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(unicodedata.category(ch) == "Cf" for ch in text):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_markers_expand_in_the_loaded_content() -> None:
    _, case = find_case("page.tag_smuggling")
    assert case.page is not None and "{{tags:" not in case.page.html
    assert any(0xE0000 <= ord(ch) <= 0xE007F for ch in case.page.html)


def test_loader_rejects_bad_data(tmp_path: Path) -> None:
    (tmp_path / "scenarios").mkdir()
    bad = tmp_path / "scenarios" / "x.toml"
    bad.write_text(
        '[scenario]\nid = "x"\ntitle = "X"\nsummary = "s"\napp = "support"\n'
        'developer_instructions = "d"\n[[case]]\nid = "x.a"\nkind = "attack"\n'
        'user_request = "hi"\n',
        encoding="utf-8",
    )
    with pytest.raises(ScenarioError, match="needs a success check"):
        load_scenario(bad, tmp_path)
    with pytest.raises(ScenarioError):
        parse_article("no front matter", "a")
