"""SecuLayer's per-app policy, loaded from a scenario's [policy] table (docs/PLAN.md §6.6)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

DEFAULT_INTENT_WORDS = ("send", "reply", "forward", "respond", "email", "tell", "handle")


class PolicyError(ValueError):
    """The policy table is malformed."""


@dataclass(frozen=True)
class ScreeningPolicy:
    classifier_intervene: float = 0.90
    classifier_flag: float = 0.50
    judge_user: bool = False  # also send the user's own message to the judge (support chat)


@dataclass(frozen=True)
class ToolPolicy:
    outbound: bool = True
    user_intent_words: tuple[str, ...] = DEFAULT_INTENT_WORDS
    recipient_fields: tuple[str, ...] = ("to", "cc", "bcc")
    data_fields: tuple[str, ...] = ("subject", "body")


@dataclass(frozen=True)
class Policy:
    protected_values: tuple[str, ...] = ()
    # What each protected value is, for copy that must never repeat the value itself.
    protected_labels: Mapping[str, str] = field(default_factory=dict)
    canary: str = ""
    allowed_domains: tuple[str, ...] = ()
    contacts: tuple[str, ...] = ()
    screening: ScreeningPolicy = field(default_factory=ScreeningPolicy)
    tools: Mapping[str, ToolPolicy] = field(default_factory=dict)
    user_name: str = "the user"  # how copy refers to the app's user: "Dana", "the customer"
    # True when the person reading the reply owns the protected values (Dana's own inbox), so
    # showing them is no leak. Image and link addresses and outbound tools still guard them.
    reader_owns_protected_values: bool = False

    @classmethod
    def from_mapping(cls, table: Mapping[str, Any]) -> Policy:
        known = {
            "protected_values",
            "protected_labels",
            "canary",
            "user_name",
            "reader_owns_protected_values",
            "allowed_domains",
            "contacts",
            "screening",
            "tools",
        }
        unknown = set(table) - known
        if unknown:
            raise PolicyError(f"unknown policy keys: {', '.join(sorted(unknown))}")

        screening_table = _table(table.get("screening", {}), "screening")
        screening = ScreeningPolicy(
            classifier_intervene=_number(
                screening_table.get("classifier_intervene", 0.90), "classifier_intervene"
            ),
            classifier_flag=_number(
                screening_table.get("classifier_flag", 0.50), "classifier_flag"
            ),
            judge_user=bool(screening_table.get("judge_user", False)),
        )
        if not 0 <= screening.classifier_flag <= screening.classifier_intervene <= 1:
            raise PolicyError("classifier thresholds must satisfy 0 <= flag <= intervene <= 1")

        tools: dict[str, ToolPolicy] = {}
        for name, raw in _table(table.get("tools", {}), "tools").items():
            tool = _table(raw, f"tools.{name}")
            tools[name] = ToolPolicy(
                outbound=bool(tool.get("outbound", True)),
                user_intent_words=_strings(
                    tool.get("user_intent_words", DEFAULT_INTENT_WORDS), "user_intent_words"
                ),
                recipient_fields=_strings(
                    tool.get("recipient_fields", ("to", "cc", "bcc")), "recipient_fields"
                ),
                data_fields=_strings(tool.get("data_fields", ("subject", "body")), "data_fields"),
            )

        canary = table.get("canary", "")
        if not isinstance(canary, str):
            raise PolicyError("canary must be a string")
        user_name = table.get("user_name", "the user")
        if not isinstance(user_name, str) or not user_name:
            raise PolicyError("user_name must be a non-empty string")
        protected = _strings(table.get("protected_values", ()), "protected_values")
        labels = dict(_table(table.get("protected_labels", {}), "protected_labels"))
        if not all(isinstance(v, str) for v in labels.values()) or set(labels) - set(protected):
            raise PolicyError("protected_labels must map protected values to strings")
        return cls(
            protected_values=protected,
            protected_labels=labels,
            canary=canary,
            user_name=user_name,
            reader_owns_protected_values=bool(table.get("reader_owns_protected_values", False)),
            allowed_domains=tuple(
                d.lower() for d in _strings(table.get("allowed_domains", ()), "allowed_domains")
            ),
            contacts=tuple(c.lower() for c in _strings(table.get("contacts", ()), "contacts")),
            screening=screening,
            tools=tools,
        )

    def label_for(self, value: str) -> str:
        """Plain-language name of a protected value: "the staff discount code"."""
        return self.protected_labels.get(value, "private data")

    def is_contact(self, address: str) -> bool:
        return address.strip().lower() in self.contacts

    def domain_allowed(self, host: str) -> bool:
        """True for an allowlisted domain or any subdomain of one."""
        host = host.lower().rstrip(".")
        return any(host == d or host.endswith("." + d) for d in self.allowed_domains)


def _table(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PolicyError(f"{name} must be a table")
    return value


def _strings(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, list | tuple):
        raise PolicyError(f"{name} must be a list of strings")
    if not all(isinstance(item, str) for item in value):
        raise PolicyError(f"{name} must be a list of strings")
    return tuple(value)


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PolicyError(f"{name} must be a number")
    return float(value)
