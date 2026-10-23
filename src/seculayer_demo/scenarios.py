"""Scenario data: TOML loading, content expansion and validation (docs/PLAN.md §5.10).

Each scenario is one TOML file in data/scenarios/, with longer content in data/content/. The
same data drives the UI, the runs and the evaluation. Content files never hold raw invisible
characters: `{{tags:…}}` and `{{zwsp}}` markers are expanded here.

Variants are separate [[case]] tables with `variant_of`; any field a variant leaves out is
inherited from its primary case.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from seculayer.policy import Policy
from seculayer.text.unicode import expand_markers
from seculayer_demo.config import REPO_ROOT

DATA_DIR = REPO_ROOT / "data"
SCENARIO_IDS = ("support", "inbox", "page", "helpdesk")
CaseKind = Literal["attack", "normal"]

SUCCESS_TYPES = {
    "secret_leaked",
    "canary_leaked",
    "tool_called",
    "url_in_reply",
    "image_in_reply",
    "reply_contains_any",
}
UTILITY_TYPES = {
    "reply_contains_any",
    "reply_mentions_all",
    "reply_lacks_secret",
    "tool_called",
    "tool_called_exactly",
    "no_tool_called",
    "links_kept",
}
INHERITED = (
    "kind",
    "tags",
    "frameworks",
    "user_request",
    "content",
    "injected_text",
    "success",
    "goal",
    "explanation",
    "why_it_works",
    "what_stops_it",
    "expected",
    "real_world",
    "hard_case",
    "hijacked_sentence",
)


class ScenarioError(ValueError):
    """The scenario data is malformed."""


@dataclass(frozen=True)
class Email:
    id: str
    sender: str  # "Northwind Logistics <updates@northwind-logistics.example>"
    subject: str
    received: str
    body: str
    format: Literal["html", "text"]
    private: bool = False
    file: str = ""

    @property
    def sender_name(self) -> str:
        return self.sender.split("<")[0].strip() or self.sender

    @property
    def sender_address(self) -> str:
        match = re.search(r"<([^>]+)>", self.sender)
        return (match.group(1) if match else self.sender).strip()


@dataclass(frozen=True)
class Article:
    id: str  # the file stem, e.g. "payroll-calendar"
    title: str
    author: str
    edited: str
    verified: bool
    body: str
    file: str = ""


@dataclass(frozen=True)
class Page:
    url: str
    html: str
    file: str = ""


@dataclass(frozen=True)
class Case:
    id: str
    scenario_id: str
    kind: CaseKind
    title: str
    user_request: str
    variant_of: str | None = None
    variants: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    injected_text: tuple[str, ...] = ()
    success: tuple[Mapping[str, Any], ...] = ()
    utility: tuple[Mapping[str, Any], ...] = ()
    goal: str = ""
    explanation: str = ""
    why_it_works: str = ""
    what_stops_it: str = ""
    expected: str = ""
    why_here: str = ""
    real_world: Mapping[str, str] = field(default_factory=dict)
    notes: str = ""
    hard_case: bool = False
    hijacked_sentence: str = ""  # banner copy when no attacker event describes the harm
    extra_email: Email | None = None
    page: Page | None = None
    articles: tuple[Article, ...] = ()  # the whole knowledge base this case retrieves from
    added_article_ids: tuple[str, ...] = ()  # poisoned articles present only in this case

    @property
    def is_attack(self) -> bool:
        return self.kind == "attack"

    @property
    def is_primary(self) -> bool:
        return self.variant_of is None


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    summary: str
    card_summary: str
    app: str
    injection: str
    user_name: str
    trifecta: Mapping[str, str]
    how_built: tuple[str, ...]
    developer_instructions: str
    policy: Policy
    cases: Mapping[str, Case]
    emails: tuple[Email, ...] = ()
    articles: tuple[Article, ...] = ()
    settings: Mapping[str, Any] = field(default_factory=dict)  # app-specific keys

    def case(self, case_id: str) -> Case:
        try:
            return self.cases[case_id]
        except KeyError:
            raise KeyError(f"unknown case {case_id!r} in scenario {self.id!r}") from None

    @property
    def attacks(self) -> list[Case]:
        return [c for c in self.cases.values() if c.is_attack and c.is_primary]

    @property
    def normal_cases(self) -> list[Case]:
        return [c for c in self.cases.values() if not c.is_attack]


# --- Loading --------------------------------------------------------------------------------


def _read(data_dir: Path, relative: str) -> str:
    path = (data_dir / relative).resolve()
    if not path.is_relative_to(data_dir.resolve()):
        raise ScenarioError(f"content path escapes data/: {relative}")
    if not path.is_file():
        raise ScenarioError(f"missing content file: {relative}")
    return expand_markers(path.read_text(encoding="utf-8"))


def _email(data_dir: Path, table: Mapping[str, Any]) -> Email:
    try:
        file = str(table["file"])
        return Email(
            id=str(table["id"]),
            sender=str(table["from"]),
            subject=str(table["subject"]),
            received=str(table["received"]),
            body=_read(data_dir, file),
            format="html" if file.endswith(".html") else "text",
            private=bool(table.get("private", False)),
            file=file,
        )
    except KeyError as missing:
        raise ScenarioError(f"email is missing {missing}") from None


def parse_article(text: str, article_id: str, file: str = "") -> Article:
    """An article file: "key: value" front matter, a line of three dashes, then the body."""
    head, sep, body = text.partition("\n---\n")
    if not sep:
        raise ScenarioError(f"article {file or article_id} has no front matter")
    fields: dict[str, str] = {}
    for line in head.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    for key in ("title", "author", "edited", "verified"):
        if key not in fields:
            raise ScenarioError(f"article {file or article_id} is missing {key}")
    return Article(
        id=article_id,
        title=fields["title"],
        author=fields["author"],
        edited=fields["edited"],
        verified=fields["verified"].lower() == "true",
        body=body.strip(),
        file=file,
    )


def _article(data_dir: Path, file: str) -> Article:
    return parse_article(_read(data_dir, file), Path(file).stem, file)


def _checks(value: object, name: str, case_id: str) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    items = [value] if isinstance(value, Mapping) else value
    if not isinstance(items, list) or not all(isinstance(i, Mapping) for i in items):
        raise ScenarioError(f"{case_id}: {name} must be a table or a list of tables")
    return tuple(items)


def _strings(value: object, name: str, case_id: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(i, str) for i in value):
        raise ScenarioError(f"{case_id}: {name} must be a list of strings")
    return tuple(value)


def load_scenario(path: Path, data_dir: Path = DATA_DIR) -> Scenario:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    meta = raw.get("scenario")
    if not isinstance(meta, Mapping):
        raise ScenarioError(f"{path.name}: missing [scenario] table")
    scenario_id = str(meta["id"])
    policy = Policy.from_mapping(raw.get("policy", {}))
    emails = tuple(_email(data_dir, table) for table in raw.get("email", []))
    articles = tuple(_article(data_dir, file) for file in meta.get("articles", []))
    known = {
        "id", "title", "summary", "card_summary", "app", "injection", "user_name", "trifecta",
        "how_built", "developer_instructions", "articles",
    }  # fmt: skip
    settings = {key: value for key, value in meta.items() if key not in known}

    tables = raw.get("case", [])
    by_id: dict[str, Mapping[str, Any]] = {}
    for table in tables:
        case_id = str(table.get("id", ""))
        if not case_id.startswith(scenario_id + "."):
            raise ScenarioError(f"case {case_id!r} must start with {scenario_id!r}.")
        if case_id in by_id:
            raise ScenarioError(f"duplicate case {case_id}")
        by_id[case_id] = table

    cases: dict[str, Case] = {}
    for case_id, table in by_id.items():
        merged = dict(table)
        parent_id = table.get("variant_of")
        if parent_id is not None:
            parent = by_id.get(parent_id)
            if parent is None or parent.get("variant_of") is not None:
                raise ScenarioError(f"{case_id}: variant_of must name a primary case")
            for key in INHERITED:
                if key not in merged and key in parent:
                    merged[key] = parent[key]
        cases[case_id] = _case(merged, scenario_id, emails, articles, data_dir)

    scenario = Scenario(
        id=scenario_id,
        title=str(meta["title"]),
        summary=str(meta["summary"]),
        card_summary=str(meta.get("card_summary", meta["summary"])),
        app=str(meta["app"]),
        injection=str(meta.get("injection", "")),
        user_name=str(meta.get("user_name", policy.user_name)),
        trifecta=dict(meta.get("trifecta", {})),
        how_built=tuple(meta.get("how_built", ())),
        developer_instructions=str(meta["developer_instructions"]),
        policy=policy,
        cases=cases,
        emails=emails,
        articles=articles,
        settings=settings,
    )
    errors = validate(scenario)
    if errors:
        raise ScenarioError(f"{path.name}: " + "; ".join(errors))
    return scenario


def _case(
    table: Mapping[str, Any],
    scenario_id: str,
    emails: tuple[Email, ...],
    articles: tuple[Article, ...],
    data_dir: Path,
) -> Case:
    case_id = str(table["id"])
    kind = table.get("kind")
    if kind not in ("attack", "normal"):
        raise ScenarioError(f"{case_id}: kind must be attack or normal")
    content = table.get("content", {})
    if not isinstance(content, Mapping):
        raise ScenarioError(f"{case_id}: content must be a table")

    extra_email = None
    if "extra_email" in content:
        extra_email = _email(data_dir, content["extra_email"])
    page = None
    if "page" in content:
        page = Page(
            str(content["url"]), _read(data_dir, str(content["page"])), str(content["page"])
        )
    kb = list(articles)
    added: list[str] = []
    for file in content.get("add", []):
        article = _article(data_dir, file)
        kb.append(article)
        added.append(article.id)
    for target, file in dict(content.get("replace", {})).items():
        index = next((i for i, a in enumerate(kb) if a.id == target), None)
        if index is None:
            raise ScenarioError(f"{case_id}: replace names unknown article {target!r}")
        article = _article(data_dir, file)
        kb[index] = article
        added.append(article.id)

    real_world = table.get("real_world", {})
    return Case(
        id=case_id,
        scenario_id=scenario_id,
        kind=kind,
        title=str(table.get("title", "")),
        user_request=str(table.get("user_request", "")),
        variant_of=table.get("variant_of"),
        variants=_strings(table.get("variants"), "variants", case_id),
        tags=_strings(table.get("tags"), "tags", case_id),
        frameworks=_strings(table.get("frameworks"), "frameworks", case_id),
        injected_text=tuple(
            expand_markers(t)
            for t in _strings(table.get("injected_text"), "injected_text", case_id)
        ),
        success=_checks(table.get("success"), "success", case_id),
        utility=_checks(table.get("utility"), "utility", case_id),
        goal=str(table.get("goal", "")),
        explanation=str(table.get("explanation", "")),
        why_it_works=str(table.get("why_it_works", "")),
        what_stops_it=str(table.get("what_stops_it", "")),
        expected=str(table.get("expected", "")),
        why_here=str(table.get("why_here", "")),
        real_world=dict(real_world) if isinstance(real_world, Mapping) else {},
        notes=str(table.get("notes", "")),
        hard_case=bool(table.get("hard_case", False)),
        hijacked_sentence=str(table.get("hijacked_sentence", "")),
        extra_email=extra_email,
        page=page,
        articles=tuple(kb) if articles else (),
        added_article_ids=tuple(added),
    )


def validate(scenario: Scenario) -> list[str]:
    errors: list[str] = []
    for case in scenario.cases.values():
        if case.is_attack:
            if not case.success:
                errors.append(f"{case.id}: an attack needs a success check")
            if not case.injected_text:
                errors.append(f"{case.id}: an attack needs injected_text")
            bad = [c.get("type") for c in case.success if c.get("type") not in SUCCESS_TYPES]
            if bad:
                errors.append(f"{case.id}: unknown success check types {bad}")
        else:
            if not case.utility:
                errors.append(f"{case.id}: a normal case needs a utility check")
            bad = [c.get("type") for c in case.utility if c.get("type") not in UTILITY_TYPES]
            if bad:
                errors.append(f"{case.id}: unknown utility check types {bad}")
        if not case.user_request:
            errors.append(f"{case.id}: user_request is empty")
        for variant in case.variants:
            other = scenario.cases.get(variant)
            if other is None or other.variant_of != case.id:
                errors.append(
                    f"{case.id}: variant {variant} must exist with variant_of = {case.id}"
                )
        if case.variant_of and case.id not in scenario.cases[case.variant_of].variants:
            errors.append(f"{case.id}: not listed in {case.variant_of}'s variants")
        if scenario.app == "inbox" and case.extra_email is None:
            errors.append(f"{case.id}: inbox cases need an extra_email")
        if scenario.app == "page" and case.page is None:
            errors.append(f"{case.id}: page cases need a page")
    return errors


@lru_cache(maxsize=4)
def load_all(data_dir: Path = DATA_DIR) -> dict[str, Scenario]:
    scenarios = {}
    for scenario_id in SCENARIO_IDS:
        scenarios[scenario_id] = load_scenario(
            data_dir / "scenarios" / f"{scenario_id}.toml", data_dir
        )
    return scenarios


def find_case(case_id: str, data_dir: Path = DATA_DIR) -> tuple[Scenario, Case]:
    scenario_id = case_id.split(".", 1)[0]
    scenarios = load_all(data_dir)
    if scenario_id not in scenarios:
        raise KeyError(f"unknown scenario {scenario_id!r}")
    scenario = scenarios[scenario_id]
    return scenario, scenario.case(case_id)


def all_cases(data_dir: Path = DATA_DIR) -> list[Case]:
    return [case for s in load_all(data_dir).values() for case in s.cases.values()]
