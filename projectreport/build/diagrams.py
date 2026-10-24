"""Diagram sources for the project report. One function per diagram; every box and arrow was
checked against the code it names (src/seculayer, src/seculayer_demo, web/src) at commit 105fe24.

Render all:  uv run --no-project --with matplotlib python diagrams.py <out-dir>
Colours follow the app's design tokens (web/src/styles/tokens.css): grey for developer text,
plum for the user, amber for outside content, red for the attacker or a stop, green for SecuLayer
and blue for system parts and decisions.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["font.family"] = "Liberation Sans"

INK, INK2, INK3 = "#10151C", "#3F4A58", "#5E6875"
BORDER, MUTED = "#C2C9D3", "#F5F7FA"
DEV = ("#3A4656", "#F1F3F6")
USER = ("#7A2A8C", "#F8F0FA")
OUT = ("#8A4600", "#FFF6E5")
BAD = ("#B42318", "#FEF2F1")
SAFE = ("#0F6B3E", "#ECF8F1")
ACC = ("#2347D6", "#EEF2FE")
GREY = (INK2, "#FFFFFF")

OUTDIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
PT = 10 / 72  # data units per point: every canvas has 10 data units per inch


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w * 10)
    ax.set_ylim(0, h * 10)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, body="", colour=GREY, ts=9.5, bs=8, align="center", lw=1.2, dashed=False):
    """A rounded box whose title and body are centred vertically as one block."""
    ec, fc = colour
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=1.0",
                                fc=fc, ec=ec, lw=lw, ls="--" if dashed else "-"))
    nt = title.count("\n") + 1
    nb = body.count("\n") + 1 if body else 0
    th = nt * ts * 1.18 * PT
    bh = nb * bs * 1.32 * PT
    gap = 0.9 if body else 0
    top = y + h / 2 + (th + gap + bh) / 2
    cx = x + w / 2 if align == "center" else x + 1.4
    tcol = INK if ec == INK2 else ec
    ax.text(cx, top, title, ha=align, va="top", fontsize=ts, fontweight="bold", color=tcol, linespacing=1.1)
    if body:
        ax.text(cx, top - th - gap, body, ha=align, va="top", fontsize=bs, color=INK2, linespacing=1.3)


def arrow(ax, p, q, colour=INK2, ls="-", lw=1.2, rad=0.0, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=11, color=colour, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))


def label(ax, x, y, text, ha="center", va="center", colour=INK3, size=7.5, bg=True):
    ax.text(x, y, text, ha=ha, va=va, fontsize=size, color=colour, linespacing=1.2,
            bbox=dict(fc="white", ec="none", pad=0.5) if bg else None)


def save(fig, name):
    fig.savefig(OUTDIR / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.08, facecolor="white")
    plt.close(fig)
    print("saved", name)


# ------------------------------------------------------------------------------------------------
def architecture():
    fig, ax = canvas(10, 9.4)
    box(ax, 1, 80, 98, 12, "Browser: Attack Lab (React 19, TypeScript, Vite, Tailwind CSS 4)",
        "Home · Lab (case list, setup panel, two run columns, prompt preview) · NDJSON stream reader · useRun event reducer\n"
        "toy-app HTML only in sandboxed iframes · replies rendered without images or live outside links", ACC)
    arrow(ax, (32, 80), (32, 72))
    label(ax, 30.5, 76, "GET /api/scenarios · POST /api/runs\nPOST /api/runs/{id}/decision · POST /api/screen", ha="right")
    arrow(ax, (68, 72), (68, 80))
    label(ax, 69.5, 76, "run events, streamed as\nnewline-delimited JSON", ha="left")
    box(ax, 1, 58, 98, 14, "FastAPI server, bound to 127.0.0.1 (src/seculayer_demo/server)",
        "routes.py: scenarios, runs, decision, screen, meta, health · runs.py: run service, paused-run store (10-minute TTL),\n"
        "classifier pre-warm · security.py: CSP, Referrer-Policy and nosniff on every response · serves the built frontend")
    arrow(ax, (50, 58), (50, 54))
    box(ax, 1, 42, 98, 12, "AgentRunner (runner.py): one case, with or without SecuLayer",
        "rebuilds the app's naive prompt before every model call · streams run.started, layer.verdict, model.request/response,\n"
        "tool.proposed/decision, run.paused, attacker.event and run.finished · decides the outcome and the banner")
    box(ax, 1, 18, 31, 20, "Toy apps (apps/)",
        "Support chat · Inbox assistant\nPage summarizer · HelpDesk\nmock mail tools, BM25 retrieval,\nnaive renderer (attacker events)", OUT)
    box(ax, 34.5, 18, 31, 20, "SecuLayer library (src/seculayer)",
        "1 Hidden-text cleaner · 2 Screening\n3 Prompt hardening · 4 Tool guard\n5 Output guard\nimports no web or OpenAI code", SAFE)
    box(ax, 68, 18, 31, 20, "Model gateway (gateway/)",
        "replay · record · live\ncanonical request → SHA-256 key\ntoken budget, pricing, 60 s timeout,\n2 retries; FakeModel for tests", ACC)
    for x in (16.5, 50, 83.5):
        arrow(ax, (x, 42), (x, 38))
    box(ax, 1, 0.5, 19, 13, "Scenario data", "data/scenarios/*.toml\ndata/content/", DEV, ts=8.5, bs=7.5)
    box(ax, 22.5, 0.5, 19, 13, "Prompt Guard 2 22M", "int8 ONNX on onnxruntime\nscore cache (JSONL)", SAFE, ts=8.5, bs=7.5)
    box(ax, 44, 0.5, 19, 13, "OpenAIJudge", "LLM judge, strict JSON\nschema, via the gateway", SAFE, ts=8.5, bs=7.5)
    box(ax, 65.5, 0.5, 15, 13, "Recordings", "data/recordings/\n{model}/*.jsonl.gz", DEV, ts=8.5, bs=7.5)
    box(ax, 83, 0.5, 16, 13, "OpenAI API", "Responses API\n(live and record\nmodes only)", BAD, ts=8.5, bs=7.5, dashed=True)
    arrow(ax, (10, 18), (10, 13.5))
    arrow(ax, (42, 18), (34, 13.5))
    arrow(ax, (55, 18), (53.5, 13.5))
    arrow(ax, (63, 9), (70, 18), rad=0.25)
    arrow(ax, (76, 18), (73, 13.5))
    arrow(ax, (91, 18), (91, 13.5), ls="--")
    save(fig, "dia-architecture")


def context_dfd():
    fig, ax = canvas(10, 6.0)
    box(ax, 38, 20, 24, 18, "SecuLayer demo system", "four toy apps, the five-layer\ndefense and the record/replay\nmodel gateway", ACC, ts=10.5, bs=8)
    box(ax, 1, 42, 21, 11, "Viewer or presenter", "", USER)
    box(ax, 78, 42, 21, 11, "OpenAI Responses API", "", BAD, dashed=True)
    box(ax, 1, 5, 21, 11, "Developer (operator)", "", DEV)
    box(ax, 78, 5, 21, 11, "Hugging Face", "pinned classifier files", GREY, dashed=True)
    arrow(ax, (22, 49), (38, 36))
    arrow(ax, (38, 31), (22, 44))
    label(ax, 32, 56.5, "choose a case, run it,\nswitch layers, approve or decline")
    label(ax, 25, 33.5, "verdicts, reply, actions,\nattacker's-server panel")
    arrow(ax, (62, 36), (78, 49))
    arrow(ax, (78, 44), (62, 31))
    label(ax, 68, 56.5, "model requests\n(live and record only)")
    label(ax, 75, 33.5, "responses and\ntoken usage")
    arrow(ax, (22, 12), (38, 23))
    label(ax, 25, 21.5, "make record, make eval,\n./run.sh, doctor")
    arrow(ax, (78, 12), (62, 23))
    label(ax, 75, 21.5, "model.quant.onnx and\ntokenizer.json, SHA-256 checked")
    ax.text(50, 1, "Dashed: outside the laptop. Every other flow stays on 127.0.0.1, and every fake domain ends in .example.",
            ha="center", fontsize=7.5, color=INK3)
    save(fig, "dia-context")


def pipeline():
    fig, ax = canvas(10, 6.4)
    label(ax, 7, 58.5, "prompt parts,\nlabelled by the app", bg=False)
    box(ax, 0.5, 49.5, 13, 5.5, "Developer\ninstructions", "", DEV, ts=7.5)
    box(ax, 0.5, 43, 13, 5.5, "User's request", "", USER, ts=7.5)
    box(ax, 0.5, 36.5, 13, 5.5, "Outside content", "", OUT, ts=7.5)
    for yy in (52.25, 45.75, 39.25):
        arrow(ax, (13.5, yy), (17, yy))
    box(ax, 17, 36.5, 12.5, 18.5, "1 Hidden-text\ncleaner", "removes hidden\nHTML, comments,\ninvisible Unicode", SAFE, ts=8.5, bs=7.2)
    box(ax, 32.5, 36.5, 12.5, 18.5, "2 Screening", "rules, classifier,\nLLM judge", SAFE, ts=8.5, bs=7.2)
    box(ax, 48, 36.5, 12.5, 18.5, "3 Prompt\nhardening", "marks outside\ncontent; adds the\ntrust policy", SAFE, ts=8.5, bs=7.2)
    box(ax, 64, 40, 11, 12, "The model", "gpt-5.4-mini\nrecorded or live", ACC, ts=8.5, bs=7.2)
    box(ax, 78.5, 40, 10.5, 12, "5 Output\nguard", "final reply", SAFE, ts=8.5, bs=7.2)
    box(ax, 91, 40, 8.5, 12, "Reply\nshown", "", GREY, ts=8.5)
    for a, b in ((29.5, 32.5), (45, 48), (60.5, 64), (75, 78.5), (89, 91)):
        arrow(ax, (a, 46), (b, 46))
    box(ax, 64, 18, 11, 12, "4 Tool\nguard", "every proposed\ntool call", SAFE, ts=8.5, bs=7.2)
    arrow(ax, (69.5, 40), (69.5, 30))
    label(ax, 71, 35, "tool call", ha="left")
    box(ax, 40, 19, 18, 10, "Mock tool runs", "its result is new\noutside content", OUT, ts=8.5, bs=7.2)
    arrow(ax, (64, 24), (58, 24))
    label(ax, 52, 32, "allowed, or Dana approved")
    arrow(ax, (40, 24), (23.25, 36.5), rad=-0.3)
    label(ax, 11, 27, "the tool result passes\nlayers 1-3 before the\nmodel reads it")
    box(ax, 19, 1, 21, 8, "Blocked: the run stops", "", BAD, ts=8.5)
    box(ax, 61, 1, 25, 8, "Asked Dana: the run pauses", "", ACC, ts=8)
    arrow(ax, (38.75, 36.5), (33, 9), colour=BAD[0], ls="--")
    label(ax, 31.5, 18, "intervene on the\nuser's message", ha="right", colour=BAD[0])
    arrow(ax, (65, 18), (40, 6), colour=BAD[0], ls="--")
    label(ax, 55, 15, "block", colour=BAD[0])
    arrow(ax, (72, 18), (72, 9), colour=ACC[0], ls="--")
    label(ax, 73.5, 13.5, "confirm", ha="left", colour=ACC[0])
    ax.text(57, 61, "Screening that intervenes on an outside item replaces the item with a placeholder (Withheld); the run continues.",
            ha="center", fontsize=7.5, color=INK3)
    save(fig, "dia-pipeline")


def sequence():
    actors = ["Browser", "Server\n(routes, runs)", "AgentRunner", "Inbox app", "SecuLayer", "OpenAIJudge", "Model gateway\n(recordings)"]
    xs = [6, 20, 34, 48, 62, 77, 92]
    steps = [
        (0, 1, "POST /api/runs {case, protected: true, trial}", "-"),
        (1, 2, "start the run generator", "-"),
        (2, 4, "inspect(user message): layers 1 and 2 pass", "-"),
        (2, 4, "harden(layout): trust policy appended", "-"),
        (2, 6, "model call 1", "-"),
        (6, 2, "tool call: list_unread_emails()", "--"),
        (2, 4, "review_tool_call: passed (it only reads data)", "-"),
        (2, 3, "execute_tool", "-"),
        (3, 2, "5 emails as outside segments (raw HTML)", "--"),
        (2, 4, "inspect(emails)", "-"),
        (4, 4, "cleaner removes the two white 1 px <div> notes", "self"),
        (4, 5, "judge(5 cleaned items, mode outside)", "-"),
        (5, 6, "judge call (strict JSON schema)", "-"),
        (6, 5, "5 × benign", "--"),
        (4, 2, "verdicts: Removed, Passed", "--"),
        (2, 4, "harden: <<EXTERNAL id=…>> markers, ˆ datamarking", "-"),
        (2, 6, "model call 2", "-"),
        (6, 2, "summary of the 5 emails, no tool call", "--"),
        (2, 4, "review_output: passed", "-"),
        (2, 1, "run.finished: stopped, stopped_by = hidden_text", "--"),
        (1, 0, "NDJSON event stream (every event above, as it happens)", "--"),
    ]
    h = 1.0 + 0.42 * len(steps)
    fig, ax = canvas(10, h)
    top = h * 10 - 2
    for x, name in zip(xs, actors):
        sec = name == "SecuLayer"
        ax.add_patch(FancyBboxPatch((x - 6, top - 5), 12, 5, boxstyle="round,pad=0.0,rounding_size=1",
                                    fc=SAFE[1] if sec else MUTED, ec=SAFE[0] if sec else INK2, lw=1))
        ax.text(x, top - 2.5, name, ha="center", va="center", fontsize=8, fontweight="bold", color=INK)
        ax.plot([x, x], [1, top - 5], color=BORDER, lw=1, zorder=0)
    y = top - 8.5
    for a, b, text, kind in steps:
        if kind == "self":
            ax.add_patch(FancyArrowPatch((xs[a], y + 0.6), (xs[a], y - 1.6), arrowstyle="-|>", mutation_scale=9,
                                         connectionstyle="arc3,rad=-1.2", color=SAFE[0], lw=1))
            ax.text(xs[a] + 3, y - 0.5, text, fontsize=7.5, color=SAFE[0], va="center")
        else:
            colour = INK2 if kind == "-" else INK3
            ax.add_patch(FancyArrowPatch((xs[a], y), (xs[b], y), arrowstyle="-|>", mutation_scale=9, color=colour,
                                         lw=1, ls="-" if kind == "-" else "--"))
            ax.text((xs[a] + xs[b]) / 2, y + 0.35, text, ha="center", va="bottom", fontsize=7.3, color=INK,
                    bbox=dict(fc="white", ec="none", pad=0.3))
        y -= 4.2
    save(fig, "dia-sequence")


def tool_guard():
    fig, ax = canvas(10, 7.8)
    box(ax, 28, 71, 44, 6, "The model proposes a tool call", "", GREY, ts=9)
    box(ax, 22, 60, 50, 7, "Is the tool outbound in the policy?", "", ACC, ts=8.5)
    arrow(ax, (47, 71), (47, 67))
    box(ax, 80, 60, 19, 7, "Passed", "read-only tool", SAFE, ts=8.5, bs=7.2)
    arrow(ax, (72, 63.5), (80, 63.5))
    label(ax, 76, 65.5, "no")
    box(ax, 22, 47, 50, 9, "1 Task permission: does the user's own message\nask to send, reply, forward, respond, email, tell or handle?", "", ACC, ts=8)
    arrow(ax, (47, 60), (47, 56))
    label(ax, 49, 58, "yes", ha="left")
    box(ax, 80, 47.5, 19, 8, "Blocked", "no request to\nsend anything", BAD, ts=8.5, bs=7.2)
    arrow(ax, (72, 51.5), (80, 51.5))
    label(ax, 76, 53.5, "no")
    box(ax, 22, 35, 50, 8, "2 Recipients: is every address a contact\nor written in the user's message?", "", ACC, ts=8)
    arrow(ax, (47, 47), (47, 43))
    label(ax, 49, 45, "yes", ha="left")
    box(ax, 22, 23, 50, 8, "3 Provenance: did an address or URL come from\noutside content, not from the user or the contacts?", "", ACC, ts=8)
    arrow(ax, (47, 35), (47, 31))
    box(ax, 80, 23, 19, 8, "Blocked", "the value came from\ncontent screening flagged", BAD, ts=8.5, bs=7.2)
    arrow(ax, (72, 27), (80, 27))
    label(ax, 76, 30.5, "yes, and\nflagged", size=7)
    box(ax, 22, 11, 50, 8, "4 Data: a protected value, or 40+ characters copied\nfrom a private email, going to a non-contact?", "", ACC, ts=8)
    arrow(ax, (47, 23), (47, 19))
    box(ax, 0.5, 11, 14, 32, "Confirm\nreasons", "each\n\"no\" in 2,\n\"yes, not\nflagged\" in 3\nand \"yes\" in 4\nadds one", GREY, ts=8.5, bs=7.2)
    for yy, text in ((39, "no"), (27, "yes, not\nflagged"), (15, "yes")):
        arrow(ax, (22, yy), (14.5, yy))
        label(ax, 18.25, yy + 2.6, text, size=7)
    box(ax, 30, 0.5, 34, 7, "Any confirm reasons?", "", ACC, ts=8.5)
    arrow(ax, (47, 11), (47, 7.5))
    arrow(ax, (14.5, 12), (30, 5.5), ls="--")
    box(ax, 0.5, 0.5, 20, 7, "yes: Asked Dana,\nthe run pauses", "", ACC, ts=8)
    arrow(ax, (30, 2.5), (20.5, 2.5))
    box(ax, 76, 0.5, 23, 7, "no: Passed, the tool runs", "", SAFE, ts=8)
    arrow(ax, (64, 4), (76, 4))
    save(fig, "dia-tool-guard")


def screening():
    fig, ax = canvas(10, 5.0)
    box(ax, 0.5, 19, 18, 13, "Item to screen", "the user's message, or\none outside item\n(after cleaning)", GREY, ts=9, bs=7.5)
    box(ax, 25, 36, 24, 11, "Rules (7, plus Base64\nand hex rescans)", "on NFKC, lowercased text\nwith invisible characters removed", SAFE, ts=8.5, bs=7.2)
    box(ax, 25, 20, 24, 11, "Prompt Guard 2 22M", "score ≥ 0.90: intervene\n0.50 to 0.90: flag", SAFE, ts=8.5, bs=7.2)
    box(ax, 25, 4, 24, 11, "LLM judge", "malicious: intervene\nsuspicious or unavailable: flag", SAFE, ts=8.5, bs=7.2)
    for yy in (41.5, 25.5, 9.5):
        arrow(ax, (18.5, 25.5), (25, yy))
    box(ax, 55, 20, 14, 11, "Strongest\ndecision wins", "", ACC, ts=8.5)
    for yy in (41.5, 25.5, 9.5):
        arrow(ax, (49, yy), (55, 25.5))
    box(ax, 75.5, 36, 24, 11, "Blocked", "intervene on the user's\nmessage: the run stops", BAD, ts=8.5, bs=7.2)
    box(ax, 75.5, 20, 24, 11, "Withheld", "intervene on an outside item:\nit becomes a placeholder", BAD, ts=8.5, bs=7.2)
    box(ax, 75.5, 4, 24, 11, "Flagged or Passed", "prompt unchanged; flags feed\nthe tool and output guards", SAFE, ts=8.5, bs=7.2)
    for yy in (41.5, 25.5, 9.5):
        arrow(ax, (69, 25.5), (75.5, yy))
    save(fig, "dia-screening")


def replay():
    fig, ax = canvas(10, 5.2)
    box(ax, 0.5, 39, 19, 10, "Model request", "from a toy app\nor the judge", GREY, ts=9, bs=7.5)
    box(ax, 25, 39, 26, 10, "Canonical request", "sorted keys, response-item ids\ndropped; key = SHA-256, plus trial", ACC, ts=9, bs=7.2)
    arrow(ax, (19.5, 44), (25, 44))
    box(ax, 57, 39, 15, 10, "Mode?", "", ACC, ts=10)
    arrow(ax, (51, 44), (57, 44))
    box(ax, 80, 39, 19.5, 10, "Live: call OpenAI", "budget check first;\nsaves nothing", BAD, ts=8.5, bs=7.2, dashed=True)
    arrow(ax, (72, 44), (80, 44))
    label(ax, 76, 46, "live")
    box(ax, 49, 21, 31, 10, "Look up (key, trial)", "in replay, a variant recorded once\nfalls back to trial 1", DEV, ts=8.5, bs=7.2)
    arrow(ax, (64.5, 39), (64.5, 31))
    label(ax, 66, 35, "replay or record", ha="left")
    box(ax, 85, 21, 14.5, 10, "Recorded\nresponse", "", SAFE, ts=8.5)
    arrow(ax, (80, 26), (85, 26))
    label(ax, 82.5, 28, "hit")
    box(ax, 45, 2, 24, 10, "Replay: ReplayMiss", "the UI says \"not recorded\"", BAD, ts=8.5, bs=7.2)
    arrow(ax, (57, 21), (57, 12))
    label(ax, 55.5, 16.5, "miss in replay", ha="right")
    box(ax, 75, 2, 24.5, 10, "Record: call OpenAI", "60 s timeout, 2 retries;\nappended to *.jsonl.gz", BAD, ts=8.5, bs=7.2, dashed=True)
    arrow(ax, (74, 21), (84, 12))
    label(ax, 81, 17.5, "miss in record", ha="left")
    box(ax, 0.5, 2, 38, 30, "Why replay works offline",
        "Layers that only decide (the tool guard, the\noutput guard, screening that blocks the user's\n"
        "message) never change a model request. The\nclassifier runs live or from its committed score\n"
        "cache. Only the cleaner, withholding, hardening\nand the judge change requests, so only those\n"
        "combinations need recordings of their own.", GREY, ts=8.5, bs=7.4, align="left")
    save(fig, "dia-replay")


def data_model():
    fig, ax = canvas(10, 3.9)

    def entity(x, y, w, name, fields, colour=GREY):
        ec, fc = colour
        h = 5 + len(fields) * 8 * 1.32 * PT + 2
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.8", fc="white", ec=ec, lw=1.2))
        ax.add_patch(FancyBboxPatch((x, y + h - 5), w, 5, boxstyle="round,pad=0.0,rounding_size=0.8", fc=fc, ec=ec, lw=1.2))
        ax.text(x + w / 2, y + h - 2.5, name, ha="center", va="center", fontsize=8.5, fontweight="bold", color=INK if ec == INK2 else ec)
        ax.text(x + 1.2, y + h - 6.2, "\n".join(fields), ha="left", va="top", fontsize=7.2, color=INK2, linespacing=1.32)
        return h

    entity(0.5, 24, 26, "Scenario (data/scenarios/*.toml)", ["id, title, summary, app", "trifecta, how_built", "developer instructions", "emails, pages, KB articles"], DEV)
    entity(34, 24, 30, "Policy ([policy] table)", ["protected_values, canary", "allowed_domains, contacts", "screening thresholds, tool rules", "reader_owns_protected_values"], SAFE)
    entity(72, 24, 27.5, "Classifier score cache", ["data/cache/classifier_scores.jsonl", "SHA-256 of a text → score", "committed, so no model is needed"], SAFE)
    hb = entity(0.5, 0.5, 26, "Case", ["id, kind (attack or normal)", "user_request, content", "injected_text (ground truth)", "success and utility checks", "variants, real_world, notes"], OUT)
    entity(34, 0.5, 30, "Recording (*.jsonl.gz)", ["key: SHA-256 of the canonical request", "trial, purpose (app or judge)", "request and response JSON", "latency_ms, token usage", "model snapshot, recorded_at"], ACC)
    entity(72, 0.5, 27.5, "Run (NDJSON events)", ["run.started, layer.verdict", "model.request, model.response", "tool.proposed, tool.decision", "attacker.event, run.paused", "run.finished: outcome, stopped_by"], GREY)
    top_b = 0.5 + hb

    def rel(p, q, text, pos=(0, 0)):
        ax.plot([p[0], q[0]], [p[1], q[1]], color=INK2, lw=1, zorder=0)
        label(ax, (p[0] + q[0]) / 2 + pos[0], (p[1] + q[1]) / 2 + pos[1], text, size=7)

    rel((26.5, 30.5), (34, 30.5), "1 : 1")
    rel((13.5, 24), (13.5, top_b), "1 : n")
    rel((26.5, 6), (34, 6), "1 : n")
    rel((64, 6), (72, 6), "replayed\ninto", pos=(0, 3.5))
    rel((22, top_b), (80, 24), "its texts are scored by Prompt Guard 2", pos=(0, 0))
    save(fig, "dia-data-model")


def wireframe():
    """The Attack Lab wireframe from docs/PLAN.md §3.3, drawn in a monospace face."""
    plan = (Path(__file__).resolve().parents[2] / "docs" / "PLAN.md").read_text(encoding="utf-8")
    start = plan.index("**Attack Lab before any run (1440×900).**")
    block = plan[plan.index("```", start) + 3:]
    block = block[block.index("\n") + 1:block.index("```")]
    lines = block.rstrip("\n").split("\n")
    width = max(len(l) for l in lines)
    fig = plt.figure(figsize=(width * 0.072, len(lines) * 0.155))
    fig.text(0.0, 1.0, "\n".join(lines), family="DejaVu Sans Mono", fontsize=7.4, va="top", ha="left",
             color=INK, linespacing=1.18)
    save(fig, "dia-wireframe-lab")


if __name__ == "__main__":
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for fn in (architecture, context_dfd, pipeline, sequence, tool_guard, screening, replay, data_model, wireframe):
        fn()
