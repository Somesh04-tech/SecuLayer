"""AgentRunner: run one case through its toy app, with or without SecuLayer, and stream run
events (docs/PLAN.md §6.5, §6.9).

The runner is a generator. When the tool guard asks for confirmation it yields `run.paused`
and waits for `send(True)` (send anyway) or `send(False)` (don't send). Turning SecuLayer off
runs exactly the same app code with no checks.

The runner rebuilds the naive layout before every model call and hardens it again, so segment
IDs, and the spotlighting IDs derived from them, stay stable across calls.

In replay and record modes, events before the first app model call are held back until that
call returns, so `run.started` can say how many recorded trials exist.
"""

from __future__ import annotations

from collections.abc import Generator, Iterator
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal

from pydantic import BaseModel

from seculayer.engine import SecuLayer, blocked_reply
from seculayer.layers.tool_guard import dialog_fields
from seculayer.text.unicode import decode_tags, is_tag_char
from seculayer.types import (
    Action,
    Finding,
    HiddenPiece,
    InjectionClassifier,
    LayerId,
    LayerSwitches,
    Message,
    Source,
    ToolCall,
    Verdict,
)
from seculayer_demo.anatomy import build_anatomy, tokens_by_source
from seculayer_demo.apps import make_app
from seculayer_demo.apps.renderer import attacker_hits
from seculayer_demo.checks import CheckResult, ExecutedCall, RunOutput, attack_succeeded, task_done
from seculayer_demo.gateway import BudgetExceeded, ModelError, ModelGateway, ReplayMiss
from seculayer_demo.judge_openai import OpenAIJudge
from seculayer_demo.prompting import responses_request
from seculayer_demo.scenarios import DATA_DIR, Case, Scenario, find_case
from seculayer_demo.server.events import (
    ActionOut,
    AttackerEvent,
    Banner,
    CheckOut,
    Checks,
    Dialog,
    FindingOut,
    Highlight,
    LayerName,
    LayerStarted,
    LayerVerdict,
    ModelRequest,
    ModelResponse,
    Outcome,
    RunError,
    RunFinished,
    RunPaused,
    RunStarted,
    ToolCallOut,
    ToolDecision,
    ToolProposed,
    ToolResult,
    Usage,
)

MAX_TOOL_ROUNDS = 8
LAYER_ORDER: tuple[LayerName, ...] = (
    "hidden_text", "screening", "hardening", "tool_guard", "output_guard",
)  # fmt: skip
LAYER_NAMES: dict[str, str] = {
    "hidden_text": "the hidden-text cleaner",
    "screening": "screening",
    "hardening": "prompt hardening",
    "tool_guard": "the tool guard",
    "output_guard": "the output guard",
}
NOT_RECORDED = (
    "This combination of layers wasn't recorded. Reset the layers, or switch to live mode."
)
ConfirmPolicy = Literal["ask", "stop", "approve", "decline"]
Event = BaseModel


@dataclass(frozen=True)
class RunRequest:
    case_id: str
    protected: bool
    model: str
    layers: LayerSwitches = field(default_factory=LayerSwitches)
    trial: int = 1
    on_confirm: ConfirmPolicy = "ask"  # "stop" ends a paused run (the evaluation; no person)
    custom_text: str | None = None  # the Sandbox: the viewer's own attacker text (live only)


@dataclass
class _Action:
    call_id: str
    name: str
    arguments: dict[str, Any]
    status: Literal["done", "blocked", "awaiting_approval", "declined"]


@dataclass
class _Intervention:
    layer: LayerName
    kind: str  # "removed", "withheld", "blocked", "confirm", "declined", "redacted"
    reason: str


def layer_switches(values: dict[str, bool] | None) -> LayerSwitches:
    return LayerSwitches(**(values or {}))


def _finding_out(finding: Finding) -> FindingOut:
    return FindingOut(
        detector=finding.detector,
        segment_id=finding.segment_id,
        span=finding.span,
        excerpt=finding.excerpt,
        score=finding.score,
        explanation=finding.explanation,
        decision=finding.decision,
    )


def with_custom_text(scenario: Scenario, case: Case, text: str) -> Case:
    """The case with its attacker-controlled content replaced by the viewer's text (Sandbox).

    Support chat: the customer's message. Inbox: the fifth (attacker) email's body. Page: the
    page HTML. HelpDesk: the body of the case's poisoned article. The success checks stay the
    case's own. Only the support chat marks the text as injected: elsewhere the viewer may keep
    harmless text, and `injected` parts are ground truth only (docs/PLAN.md §6.9).
    """
    if scenario.app == "support":
        return replace(case, user_request=text, injected_text=(text,))
    if scenario.app == "inbox" and case.extra_email is not None:
        return replace(case, extra_email=replace(case.extra_email, body=text), injected_text=())
    if scenario.app == "page" and case.page is not None:
        return replace(case, page=replace(case.page, html=text), injected_text=())
    if scenario.app == "helpdesk" and case.added_article_ids:
        target = case.added_article_ids[0]
        articles = tuple(replace(a, body=text) if a.id == target else a for a in case.articles)
        return replace(case, articles=articles, injected_text=())
    raise ValueError(f"{case.id} has no attacker-controlled content to replace")


def readable(text: str) -> str:
    """Injected text as a person would read it: tag characters decoded to ASCII."""
    return decode_tags(text) if text and all(is_tag_char(ch) for ch in text) else text


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text and not text[:2].isupper() else text


class AgentRunner:
    def __init__(
        self,
        request: RunRequest,
        *,
        gateway: ModelGateway,
        judge_model: str,
        classifier: InjectionClassifier | None,
        run_id: str,
        data_dir: Any = DATA_DIR,
    ) -> None:
        self.request = request
        self.gateway = gateway
        self.judge_model = judge_model
        self.classifier = classifier
        self.run_id = run_id
        scenario, case = find_case(request.case_id, data_dir)
        if request.custom_text is not None:
            case = with_custom_text(scenario, case, request.custom_text)
        self.scenario: Scenario = scenario
        self.case: Case = case
        self.policy = scenario.policy
        self.seed = case.id  # trials share prompts; the trial number is part of the key
        self.app = make_app(scenario, case, seed=self.seed)

        self.judge: OpenAIJudge | None = None
        self.guard: SecuLayer | None = None
        layers = request.layers
        if request.protected:
            if layers.screening and layers.judge:
                self.judge = OpenAIJudge(
                    gateway,
                    model=judge_model,
                    seed=self.seed,
                    trial=request.trial,
                    scenario=scenario.id,
                    case_id=case.id,
                )
            self.guard = SecuLayer(
                self.policy,
                layers=layers,
                classifier=classifier,
                judge=self.judge,
                seed=self.seed,
            )

        self._queue: list[Event] = []
        self._started = False
        self._hold = gateway.mode != "live"
        self._verdicts: dict[str, Verdict] = {}
        self._interventions: list[_Intervention] = []
        self._actions: list[_Action] = []
        self._sent: list[dict[str, Any]] = []
        self._executed: list[ExecutedCall] = []
        self._removed: list[HiddenPiece] = []
        self._cost = 0.0
        self._raw_reply = ""
        self._call_index = 0
        self._trial_used = request.trial
        self._step = 0
        self.finished: RunFinished | None = None

    # --- Event plumbing ----------------------------------------------------------------------

    def _emit(self, event: Event) -> None:
        self._queue.append(event)

    def _start_event(self, trials_available: int) -> RunStarted:
        return RunStarted(
            run_id=self.run_id,
            case_id=self.case.id,
            protected=self.request.protected,
            model=self.request.model,
            mode=self.gateway.mode,
            trial=self._trial_used,
            trials_available=trials_available,
            layers=asdict(self.request.layers),
        )

    def _drain(self, *, force: bool = False) -> Iterator[Event]:
        if self._hold and not force:
            return
        if not self._started:
            self._started = True
            yield self._start_event(0)
        queued, self._queue = self._queue, []
        yield from queued

    def _release(self, trials_available: int) -> Iterator[Event]:
        """The first app call returned: emit run.started and everything held back."""
        if not self._started:
            self._started = True
            self._hold = False
            yield self._start_event(trials_available)
        yield from self._drain()

    def _verdict(self, verdict: Verdict, step: int) -> None:
        layer: LayerName = verdict.layer.value
        self._verdicts[layer] = verdict
        self._emit(
            LayerVerdict(
                layer=layer,
                step=step,
                action=verdict.action.value,
                reason=verdict.reason,
                findings=[_finding_out(f) for f in verdict.findings],
                latency_ms=verdict.latency_ms,
                detail=list(verdict.detail),
            )
        )
        if verdict.action in (Action.BLOCKED, Action.WITHHELD):
            self._interventions.append(_Intervention(layer, verdict.action.value, verdict.reason))
        elif verdict.action is Action.REMOVED and layer == "output_guard":
            self._interventions.append(_Intervention(layer, "redacted", verdict.reason))

    def _started_layers(self, step: int, *layers: LayerName) -> None:
        for layer in layers:
            self._emit(LayerStarted(layer=layer, step=step))

    # --- The run -------------------------------------------------------------------------------

    def events(self) -> Generator[Event, bool | None, None]:
        try:
            yield from self._body()
        except ReplayMiss:
            yield from self._fail(NOT_RECORDED, retryable=False)
        except ModelError as error:
            yield from self._fail(str(error), retryable=error.retryable)
        except BudgetExceeded as error:
            yield from self._fail(f"Live calls stopped: {error}.", retryable=False)

    def _fail(self, message: str, *, retryable: bool) -> Iterator[Event]:
        self._emit(RunError(message=message, retryable=retryable))
        finished = RunFinished(
            outcome="error",
            banner=Banner(title="Error", sentence=_lower_first(message)),
            stopped_by=None,
            checks=Checks(),
            reply_markdown="",
            actions=self._action_models(),
            cost_usd=round(self._cost + self._judge_cost(), 6),
        )
        self.finished = finished
        self._emit(finished)
        yield from self._drain(force=True)

    def _body(self) -> Generator[Event, bool | None, None]:
        guard = self.guard
        case = self.case
        base = self.app.build_layout()
        developer_text = "".join(
            s.text
            for s in base.segments()
            if s.source is Source.DEVELOPER and not s.outside_scaffold
        )
        ctx = guard.new_context(case.user_request, developer_text) if guard else None
        replacements: dict[str, Any] = {}
        rounds: list[tuple[Message, ...]] = []
        step = self._step = 0

        if guard is not None and ctx is not None:
            self._started_layers(step, "hidden_text", "screening")
            inspection = guard.inspect(base.inspectable_segments(), ctx)
            self._record_cleaner(inspection.hidden)
            for verdict in inspection.verdicts:
                self._verdict(verdict, step)
            yield from self._drain()
            if inspection.blocked:
                yield from self._finish(blocked_reply(inspection.block_reason))
                return
            replacements.update({s.id: s for s in inspection.segments})

        for _round in range(MAX_TOOL_ROUNDS + 1):
            layout = base.replace_segments(list(replacements.values()))
            for round_messages in rounds:
                layout = layout.append(*round_messages)
            request_layout = layout
            if guard is not None and ctx is not None:
                self._started_layers(step, "hardening")
                request_layout, verdict = guard.harden(layout, ctx)
                self._verdict(verdict, step)
            request = responses_request(request_layout, self.app.tool_specs, self.request.model)
            anatomy = build_anatomy(
                request_layout, case.injected_text, self._removed if guard else ()
            )
            index = self._call_index
            self._call_index += 1
            self._emit(
                ModelRequest(
                    call_index=index, anatomy=anatomy, tokens_by_source=tokens_by_source(anatomy)
                )
            )
            yield from self._drain()

            result = self.gateway.call(
                request, trial=self.request.trial, scenario=self.scenario.id, case_id=case.id
            )
            self._cost += result.cost_usd
            if index == 0:
                self._trial_used = result.trial
            self._emit(
                ModelResponse(
                    call_index=index,
                    output_text=result.output_text,
                    tool_calls=[
                        ToolCallOut(call_id=c.call_id, name=c.name, arguments=c.arguments)
                        for c in result.tool_calls
                    ],
                    latency_ms=result.latency_ms,
                    usage=Usage(
                        input_tokens=result.usage.get("input_tokens", 0),
                        output_tokens=result.usage.get("output_tokens", 0),
                        cached_tokens=result.usage.get("cached_tokens", 0),
                    ),
                    recorded=result.recorded,
                    recorded_at=result.recorded_at,
                    trial=result.trial,
                )
            )
            if index == 0:
                yield from self._release(result.trials_available)
            else:
                yield from self._drain()

            if not result.tool_calls:
                self._raw_reply = result.output_text
                text = result.output_text
                if guard is not None and ctx is not None:
                    self._started_layers(step, "output_guard")
                    review = guard.review_output(text, ctx)
                    self._verdict(review.verdict, step)
                    text = review.text
                yield from self._finish(text)
                return

            if _round == MAX_TOOL_ROUNDS:
                yield from self._fail(
                    "The assistant kept calling tools without finishing.", retryable=False
                )
                return

            parsed = result.tool_calls[0]  # parallel tool calls are off
            call = ToolCall(parsed.call_id, parsed.name, parsed.arguments)
            self._emit(
                ToolProposed(call_id=call.call_id, name=call.name, arguments=dict(call.arguments))
            )
            action = _Action(call.call_id, call.name, dict(call.arguments), "done")
            self._actions.append(action)
            step = self._step = step + 1

            if guard is not None and ctx is not None:
                self._started_layers(step, "tool_guard")
                tool_review = guard.review_tool_call(call, ctx)
                self._verdict(tool_review.verdict, step)
                if tool_review.action == "allow":
                    leak = guard.review_tool_arguments(call, ctx)
                    if leak is not None and self.request.layers.observe_only:
                        self._verdict(leak, step)  # recorded, but observe-only changes nothing
                    elif leak is not None:
                        self._verdict(leak, step)
                        action.status = "blocked"
                        self._emit(
                            ToolDecision(call_id=call.call_id, action="block", reason=leak.reason)
                        )
                        yield from self._finish(self._blocked_call_reply(call, leak.reason))
                        return
                if tool_review.action == "block":
                    action.status = "blocked"
                    self._emit(
                        ToolDecision(
                            call_id=call.call_id, action="block", reason=tool_review.verdict.reason
                        )
                    )
                    yield from self._finish(
                        self._blocked_call_reply(call, tool_review.verdict.reason)
                    )
                    return
                if tool_review.action == "confirm":
                    self._interventions.append(
                        _Intervention("tool_guard", "confirm", tool_review.verdict.reason)
                    )
                    self._emit(
                        ToolDecision(
                            call_id=call.call_id,
                            action="confirm",
                            reason=tool_review.verdict.reason,
                        )
                    )
                    approve = yield from self._confirm(
                        call, tool_review.verdict.reason, tool_review.highlights
                    )
                    if approve is None:
                        action.status = "awaiting_approval"
                        yield from self._finish("", paused=True)
                        return
                    self._emit(
                        ToolDecision(
                            call_id=call.call_id,
                            action="approved" if approve else "declined",
                            reason=f"{self.policy.user_name} "
                            + ("approved." if approve else "declined."),
                        )
                    )
                    if not approve:
                        action.status = "declined"
                        self._interventions.append(
                            _Intervention(
                                "tool_guard", "declined", f"{self.policy.user_name} declined."
                            )
                        )
                        yield from self._finish(
                            f"I didn't send the email because {self.policy.user_name} declined."
                        )
                        return
                else:
                    self._emit(
                        ToolDecision(
                            call_id=call.call_id, action="allow", reason=tool_review.verdict.reason
                        )
                    )

            execution = self.app.execute_tool(call)
            self._executed.append(ExecutedCall(call.name, dict(call.arguments)))
            if execution.sent is not None:
                self._sent.append(dict(execution.sent))
            self._emit(ToolResult(call_id=call.call_id, summary=execution.summary))
            result_segments = list(execution.segments)
            if guard is not None and ctx is not None:
                self._started_layers(step, "hidden_text", "screening")
                inspection = guard.inspect(result_segments, ctx)
                self._record_cleaner(inspection.hidden)
                for verdict in inspection.verdicts:
                    self._verdict(verdict, step)
                result_segments = list(inspection.segments)
            yield from self._drain()

            messages: list[Message] = []
            if result.output_text:
                messages.append(Message("assistant", (), content=result.output_text))
            messages.append(
                Message(
                    "tool_call",
                    (),
                    tool_name=call.name,
                    call_id=call.call_id,
                    content=parsed.raw_arguments,
                )
            )
            messages.append(
                Message(
                    "tool_result", tuple(result_segments), tool_name=call.name, call_id=call.call_id
                )
            )
            rounds.append(tuple(messages))

    def _record_cleaner(self, hidden: tuple[HiddenPiece, ...]) -> None:
        """Note when the cleaner removed (part of) the attacker's injected text."""
        self._removed += hidden
        if self.request.layers.observe_only:
            return
        injected = [readable(t) for t in self.case.injected_text if t]
        for piece in hidden:
            if len(piece.text) > 8 and any(n in piece.text or piece.text in n for n in injected):
                self._interventions.append(
                    _Intervention("hidden_text", "removed", "removed the injected text")
                )
                return

    def _confirm(
        self, call: ToolCall, reason: str, highlights: tuple[Finding, ...]
    ) -> Generator[Event, bool | None, bool | None]:
        policy = self.request.on_confirm
        if policy == "stop":
            return None
        if policy in ("approve", "decline"):
            return policy == "approve"
        fields = dialog_fields(call)
        yield from self._drain(force=True)
        decision = yield RunPaused(
            run_id=self.run_id,
            call_id=call.call_id,
            dialog=Dialog(
                to=list(fields["to"]),
                subject=str(fields["subject"]),
                body=str(fields["body"]),
                highlights=[Highlight(text=f.excerpt, why=f.explanation) for f in highlights],
                reason=reason,
            ),
        )
        return bool(decision)

    def _blocked_call_reply(self, call: ToolCall, reason: str) -> str:
        if call.name == "send_email":
            to = ", ".join(str(a) for a in (call.arguments.get("to") or [])) or "nobody"
            return f"SecuLayer blocked the email to {to}. {reason}"
        return f"SecuLayer blocked the {call.name} call. {reason}"

    def _judge_cost(self) -> float:
        return sum(c.cost_usd for c in self.judge.calls) if self.judge else 0.0

    def _action_models(self) -> list[ActionOut]:
        return [
            ActionOut(call_id=a.call_id, name=a.name, arguments=a.arguments, status=a.status)
            for a in self._actions
        ]

    # --- Finishing -----------------------------------------------------------------------------

    def _close_layers(self, reached_reply: bool) -> None:
        """Give every layer a row: off, not reached, or (tool guard) nothing to check."""
        if self.guard is None:
            return
        switches = self.request.layers
        for layer in LAYER_ORDER:
            if layer in self._verdicts:
                continue
            on = getattr(switches, layer)
            if layer == "tool_guard" and on and reached_reply:
                verdict = Verdict(LayerId.TOOL_GUARD, Action.PASSED, "No actions requested.")
            elif not on:
                verdict = Verdict(LayerId(layer), Action.OFF, "Switched off.")
            else:
                verdict = Verdict(LayerId(layer), Action.NOT_REACHED, "Not reached.")
            self._verdict(verdict, self._step)

    def _finish(self, reply: str, *, paused: bool = False) -> Iterator[Event]:
        reached_reply = bool(self._raw_reply) and not paused
        self._close_layers(reached_reply)
        out = RunOutput(reply=reply, raw_reply=self._raw_reply, tool_calls=tuple(self._executed))
        for hit in attacker_hits(
            reply, self._sent, self.policy, chat=self.scenario.app == "support"
        ):
            self._emit(
                AttackerEvent(
                    channel=hit.channel,
                    destination=hit.destination,
                    data=hit.data,
                    zero_click=hit.zero_click,
                )
            )
        success = attack_succeeded(self.case, self.policy, out) if self.case.is_attack else None
        utility = task_done(self.case, self.policy, out) if not self.case.is_attack else None
        outcome, banner, stopped_by = self._outcome(success, utility, paused, out)
        finished = RunFinished(
            outcome=outcome,
            banner=banner,
            stopped_by=stopped_by,
            checks=Checks(
                success=CheckOut(passed=success.passed, detail=success.detail) if success else None,
                utility=CheckOut(passed=utility.passed, detail=utility.detail) if utility else None,
            ),
            reply_markdown=reply,
            actions=self._action_models(),
            cost_usd=round(self._cost + self._judge_cost(), 6),
        )
        self.finished = finished
        self._emit(finished)
        yield from self._drain(force=True)

    def _outcome(
        self,
        success: CheckResult | None,
        utility: CheckResult | None,
        paused: bool,
        out: RunOutput,
    ) -> tuple[Outcome, Banner, LayerName | None]:
        who = self.policy.user_name
        protected = self.request.protected
        first = self._interventions[0] if self._interventions else None

        if paused:
            to = next((a.arguments for a in self._actions if a.status == "awaiting_approval"), {})
            addresses = ", ".join(str(x) for x in (to.get("to") or [])) or "someone"
            return (
                "paused",
                Banner(
                    title="Paused",
                    sentence=f"SecuLayer asked {who} before sending an email to {addresses}.",
                ),
                "tool_guard",
            )

        if success is not None:
            if success.passed:
                return (
                    "hijacked",
                    Banner(title="Hijacked", sentence=self._hijacked_sentence(out.reply)),
                    None,
                )
            # The layer that stopped the harmful action gets the credit; otherwise the first
            # input-side layer that removed, withheld or blocked the attacker's text.
            stops = [i for i in self._interventions if i.kind != "confirm"]
            stops.sort(key=lambda i: i.layer not in ("tool_guard", "output_guard"))
            if protected and stops:
                stop = stops[0]
                sentence = f"stopped by {LAYER_NAMES[stop.layer]}. {self._stop_reason(stop)}"
                return "stopped", Banner(title="Safe", sentence=sentence.strip()), stop.layer
            if protected:
                hardened = self.request.layers.hardening
                sentence = "nothing was blocked: the model ignored the injected instructions" + (
                    ", with SecuLayer's trust policy in place." if hardened else " on its own."
                )
                return "resisted", Banner(title="Not hijacked", sentence=sentence), None
            return (
                "resisted",
                Banner(
                    title="Not hijacked this time",
                    sentence="the model ignored the injected instructions on its own.",
                ),
                None,
            )

        assert utility is not None
        if protected and first is not None:
            alarm = self._false_alarm(utility)
            if alarm is not None:
                verb, intervention = alarm
                sentence = f"SecuLayer {verb} a normal request. {self._stop_reason(intervention)}"
                return (
                    "false_alarm",
                    Banner(title="False alarm", sentence=sentence.strip()),
                    (intervention.layer),
                )
        if utility.passed:
            return (
                "completed",
                Banner(title="Done", sentence="the assistant handled the request normally."),
                None,
            )
        return (
            "failed",
            Banner(
                title="Not done", sentence=f"the assistant's answer missed what {who} asked for."
            ),
            None,
        )

    def _false_alarm(self, utility: CheckResult) -> tuple[str, _Intervention] | None:
        for intervention in self._interventions:
            if intervention.kind == "blocked":
                return "blocked", intervention
            if intervention.kind == "withheld":
                return "withheld part of", intervention
            if intervention.kind in ("confirm", "declined"):
                return "asked for confirmation on", intervention
            if intervention.kind == "redacted" and not utility.passed:
                return "removed a link or image from", intervention
        return None

    def _stop_reason(self, intervention: _Intervention) -> str:
        verdict = self._verdicts.get(intervention.layer)
        reason = verdict.reason if verdict is not None else intervention.reason
        if intervention.kind == "declined":
            reason = f"{self.policy.user_name} declined to send the email."
        return reason

    def _hijacked_sentence(self, reply: str) -> str:
        who = self.policy.user_name
        for call in self._executed:
            if call.name == "send_email":
                to = [str(a) for k in ("to", "cc", "bcc") for a in (call.arguments.get(k) or [])]
                outsiders = [a for a in to if not self.policy.is_contact(a)]
                if outsiders:
                    return f"the assistant emailed {', '.join(outsiders)} from {who}'s account."
        hits = attacker_hits(reply, [], self.policy, chat=self.scenario.app == "support")
        for hit in hits:
            if hit.channel == "image":
                return (
                    f"the reply loaded an image from {hit.destination}, sending {who}'s "
                    "private data with it."
                )
            if hit.channel == "chat":
                return f"the assistant revealed {hit.data} to the customer."
            if hit.channel == "link":
                return f"the reply gave {who} a link to {hit.destination}."
        if self.case.hijacked_sentence:
            return self.case.hijacked_sentence
        return "the assistant did what the attacker's text asked."


__all__ = ["AgentRunner", "RunRequest", "layer_switches"]
