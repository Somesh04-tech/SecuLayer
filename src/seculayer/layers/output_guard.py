"""Layer 5, the output guard: check the final reply for leaks before it is shown
(docs/PLAN.md §6.2).

1. Canary: the canary string appears -> block.
2. Protected values, after normalisation, reversed, or inside Base64 or hex runs -> block,
   unless the policy says the reader owns them (then only addresses are checked for them).
3. Images whose address isn't same-origin or allowlisted are removed (images load without a
   click, so they are the zero-click leak channel).
4. A link to a domain that isn't allowlisted is kept only if the domain appears in the trusted
   input or in the visible text of outside content that screening didn't flag, and its address
   carries no private data. Otherwise it is neutralised.
"""

from __future__ import annotations

from dataclasses import dataclass

from seculayer.text.encodings import find_secrets
from seculayer.text.urls import UrlRef, extract_urls, mentions_host, private_data_in_url
from seculayer.types import Action, Finding, RunContext, ToolCall

CANARY_LABEL = "the app's internal reference string"


@dataclass(frozen=True)
class OutputOutcome:
    text: str
    blocked: bool
    action: Action
    reason: str
    findings: tuple[Finding, ...]
    removed_urls: tuple[str, ...]


def withheld_reply(what: str) -> str:
    return f"SecuLayer withheld this reply because it contained {what}."


def _canary(text: str, ctx: RunContext) -> tuple[str, Finding] | None:
    canary = ctx.policy.canary
    if not canary or canary.lower() not in text.lower():
        return None
    at = text.lower().find(canary.lower())
    return CANARY_LABEL, Finding(
        "output:canary",
        None,
        (at, at + len(canary)),
        canary,
        None,
        "The reply repeats the canary hidden in the developer instructions.",
    )


def _protected(text: str, ctx: RunContext) -> tuple[str, Finding] | None:
    for match in find_secrets(text, ctx.policy.protected_values):
        label = ctx.policy.label_for(match.value)
        return label, Finding(
            "output:protected_value",
            None,
            None,
            "",
            None,
            f"The reply contains {label} ({match.how}).",
        )
    return None


def leaks(text: str, ctx: RunContext) -> tuple[str, Finding] | None:
    """The first canary or protected-value leak in `text`, as (what, finding)."""
    return _canary(text, ctx) or _protected(text, ctx)


def _blocked(what: str, finding: Finding) -> OutputOutcome:
    return OutputOutcome(
        withheld_reply(what), True, Action.BLOCKED, f"The reply contained {what}.", (finding,), ()
    )


def review(text: str, ctx: RunContext) -> OutputOutcome:
    canary = _canary(text, ctx)
    if canary is not None:
        return _blocked(*canary)

    # Images and links first: private data inside an address removes that address (the zero-
    # and one-click leak channels). Whatever is left is then checked for protected values.
    policy = ctx.policy
    trusted = "\n".join((ctx.user_text, ctx.developer_text))
    visible = "\n".join(
        text
        for seg_id, text in ctx.visible_outside.items()
        if seg_id not in ctx.flagged_segment_ids
    )
    findings: list[Finding] = []
    removed: list[UrlRef] = []
    reasons: list[str] = []
    for ref in extract_urls(text):
        host = ref.host
        if not host or policy.domain_allowed(host):
            continue
        private = private_data_in_url(ref.url, policy.protected_values)
        carried = f" Its address carried {policy.label_for(private[0].value)}." if private else ""
        if ref.kind == "image":
            removed.append(ref)
            reasons.append(f"Removed an image from {host}.{carried}")
            findings.append(
                Finding(
                    "output:image",
                    None,
                    (ref.start, ref.end),
                    ref.url,
                    None,
                    f"An image from {host} would load without a click.{carried}",
                )
            )
            continue
        known = mentions_host(trusted, host) or mentions_host(visible, host)
        if known and not private:
            continue
        removed.append(ref)
        why = carried.strip() or (
            f"{host} isn't allowlisted and doesn't appear in what {policy.user_name} sees."
        )
        reasons.append(f"Removed a link to {host}. {why}")
        findings.append(
            Finding(
                "output:link", None, (ref.start, ref.end), ref.url, None, f"A link to {host}: {why}"
            )
        )

    safe = _neutralise(text, removed) if removed else text
    leak = None if policy.reader_owns_protected_values else _protected(safe, ctx)
    if leak is not None:
        return _blocked(*leak)
    if not removed:
        return OutputOutcome(text, False, Action.PASSED, "No secrets or outside links.", (), ())
    return OutputOutcome(
        safe,
        False,
        Action.REMOVED,
        " ".join(dict.fromkeys(reasons)),
        tuple(findings),
        tuple(ref.url for ref in removed),
    )


def review_tool_arguments(call: ToolCall, ctx: RunContext) -> OutputOutcome | None:
    """A leak of the canary in an outbound tool argument, or None.

    Protected values in tool arguments are the tool guard's job (its data check asks the user),
    so this check covers only the developer instructions leaking.
    """
    policy = ctx.policy
    if not policy.canary:
        return None
    for value in call.arguments.values():
        if isinstance(value, str) and policy.canary.lower() in value.lower():
            finding = Finding(
                "output:canary",
                None,
                None,
                policy.canary,
                None,
                "A tool argument repeats the canary.",
            )
            return OutputOutcome(
                "",
                True,
                Action.BLOCKED,
                f"The {call.name} call contained {CANARY_LABEL}.",
                (finding,),
                (),
            )
    return None


def _neutralise(text: str, refs: list[UrlRef]) -> str:
    out, cursor = [], 0
    for ref in sorted(refs, key=lambda r: r.start):
        out.append(text[cursor : ref.start])
        if ref.kind == "image":
            out.append(f"[image removed by SecuLayer: {ref.host}]")
        elif ref.kind == "link" and ref.text and ref.text != ref.url:
            out.append(f"{ref.text} (link removed by SecuLayer: {ref.host})")
        else:
            out.append(f"(link removed by SecuLayer: {ref.host})")
        cursor = ref.end
    out.append(text[cursor:])
    return "".join(out)
