"""The injection classifier: Meta Llama Prompt Guard 2 22M, run locally with onnxruntime.

docs/PLAN.md §6.2. Scores are the probability of label 1 (MALICIOUS). Text longer than one
512-token window is split into overlapping windows and the highest score wins.

onnxruntime, tokenizers and numpy are optional: they're imported only when the model loads,
so the library works without them (screening then uses recorded scores, or reports the
classifier as unavailable).

Scores are cached by the SHA-256 of the text in a JSONL file. The demo commits that file
(data/cache/classifier_scores.jsonl), so a machine without the model still has recorded
scores for every curated input.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from seculayer.types import ClassifierUnavailable, ScoreSource

MODEL_NAME = "prompt-guard-2-22m"
MODEL_FILE = "model.quant.onnx"
TOKENIZER_FILE = "tokenizer.json"
WINDOW_TOKENS = 512
OVERLAP_TOKENS = 64
MALICIOUS_LABEL = 1


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def softmax(logits: Sequence[float]) -> list[float]:
    peak = max(logits)
    exps = [math.exp(value - peak) for value in logits]
    total = sum(exps)
    return [value / total for value in exps]


def split_windows(token_ids: Sequence[int], content_size: int, overlap: int) -> list[list[int]]:
    """Split content tokens into windows of at most `content_size`, overlapping by `overlap`.

    An empty input still gets one (empty) window, so every text has a score.
    """
    if content_size <= overlap:
        raise ValueError("window content size must be larger than the overlap")
    ids = list(token_ids)
    if len(ids) <= content_size:
        return [ids]
    stride = content_size - overlap
    windows = []
    start = 0
    while True:
        windows.append(ids[start : start + content_size])
        if start + content_size >= len(ids):
            return windows
        start += stride


class PromptGuardClassifier:
    """Implements seculayer.types.InjectionClassifier. Loads the model on first use."""

    name = MODEL_NAME

    def __init__(
        self,
        model_dir: Path,
        *,
        threads: int = 2,
        window_tokens: int = WINDOW_TOKENS,
        overlap_tokens: int = OVERLAP_TOKENS,
    ) -> None:
        self.model_dir = model_dir
        self.threads = threads
        self.window_tokens = window_tokens
        self.overlap_tokens = overlap_tokens
        self._lock = threading.Lock()
        self._session: Any = None
        self._tokenizer: Any = None
        self._prefix: list[int] = []
        self._suffix: list[int] = []
        self._input_names: tuple[str, ...] = ()

    @staticmethod
    def files_present(model_dir: Path) -> bool:
        return (model_dir / MODEL_FILE).is_file() and (model_dir / TOKENIZER_FILE).is_file()

    @property
    def available(self) -> bool:
        return self.files_present(self.model_dir)

    @property
    def loaded(self) -> bool:
        return self._session is not None

    def load(self) -> None:
        with self._lock:
            if self._session is not None:
                return
            if not self.available:
                raise ClassifierUnavailable(f"model files not found in {self.model_dir}")
            import onnxruntime
            from tokenizers import Tokenizer

            tokenizer = Tokenizer.from_file(str(self.model_dir / TOKENIZER_FILE))
            # The shipped tokenizer pads every input to 512 tokens, which made inference about
            # 30 times slower in the planning test. Windows are built by hand instead.
            tokenizer.no_padding()
            tokenizer.no_truncation()

            # Find the special tokens the tokenizer wraps around content ([CLS] … [SEP]).
            bare = tokenizer.encode("a", add_special_tokens=False).ids
            full = tokenizer.encode("a").ids
            at = next(i for i in range(len(full)) if full[i : i + len(bare)] == bare)
            self._prefix, self._suffix = full[:at], full[at + len(bare) :]

            options = onnxruntime.SessionOptions()
            options.intra_op_num_threads = self.threads
            options.inter_op_num_threads = 1
            session = onnxruntime.InferenceSession(
                str(self.model_dir / MODEL_FILE),
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )
            self._input_names = tuple(i.name for i in session.get_inputs())
            self._tokenizer = tokenizer
            self._session = session

    def windows(self, text: str) -> list[list[int]]:
        """The token windows scored for `text`, special tokens included."""
        self.load()
        content = self._tokenizer.encode(text, add_special_tokens=False).ids
        size = self.window_tokens - len(self._prefix) - len(self._suffix)
        return [
            self._prefix + chunk + self._suffix
            for chunk in split_windows(content, size, self.overlap_tokens)
        ]

    def score(self, text: str) -> float:
        import numpy as np

        best = 0.0
        for window in self.windows(text):
            ids = np.asarray([window], dtype=np.int64)
            feeds: dict[str, Any] = {}
            for name in self._input_names:
                if name == "input_ids":
                    feeds[name] = ids
                elif name == "attention_mask":
                    feeds[name] = np.ones_like(ids)
                elif name == "token_type_ids":
                    feeds[name] = np.zeros_like(ids)
                else:
                    raise RuntimeError(f"unexpected model input {name!r}")
            logits = self._session.run(None, feeds)[0][0]
            best = max(best, softmax([float(v) for v in logits])[MALICIOUS_LABEL])
        return best


class ScoreCache:
    """Classifier scores by SHA-256 of the text, in an append-only JSONL file."""

    def __init__(self, path: Path, model: str = MODEL_NAME) -> None:
        self.path = path
        self.model = model
        self._lock = threading.Lock()
        self._scores: dict[str, float] | None = None

    def _load(self) -> dict[str, float]:
        if self._scores is None:
            scores: dict[str, float] = {}
            if self.path.is_file():
                for line in self.path.read_text(encoding="utf-8").splitlines():
                    try:
                        entry = json.loads(line)
                        if entry.get("model") != self.model:
                            continue
                        score = float(entry["score"])
                        key = str(entry["sha256"])
                    except (ValueError, TypeError, KeyError, AttributeError):
                        continue  # tolerate damaged or foreign lines
                    if 0.0 <= score <= 1.0 and len(key) == 64:
                        scores[key] = score
            self._scores = scores
        return self._scores

    def __len__(self) -> int:
        with self._lock:
            return len(self._load())

    def get(self, text: str) -> float | None:
        with self._lock:
            return self._load().get(text_sha256(text))

    def put(self, text: str, score: float) -> None:
        key = text_sha256(text)
        with self._lock:
            scores = self._load()
            if scores.get(key) == score:
                return
            scores[key] = score
            self.path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps({"sha256": key, "score": round(score, 6), "model": self.model})
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")


class CachedClassifier:
    """Implements seculayer.types.SourcedClassifier, the classifier screening uses.

    Cache first, then the live model, then recorded scores.

    `score_with_source` says where a score came from, so the UI can show "recorded score".
    Raises ClassifierUnavailable when the model is missing and nothing was recorded.
    """

    def __init__(self, cache: ScoreCache, model: PromptGuardClassifier | None) -> None:
        self.cache = cache
        self.model = model
        self.name = model.name if model is not None else cache.model

    @property
    def model_available(self) -> bool:
        return self.model is not None and self.model.available

    def score_with_source(self, text: str) -> tuple[float, ScoreSource]:
        cached = self.cache.get(text)
        if self.model is not None and self.model.available:
            if cached is not None:
                return cached, "cached"
            score = self.model.score(text)
            self.cache.put(text, score)
            return score, "live"
        if cached is not None:
            return cached, "recorded"
        raise ClassifierUnavailable("model not downloaded and no recorded score for this text")

    def score(self, text: str) -> float:
        return self.score_with_source(text)[0]

    def warm(self, texts: Sequence[str]) -> int:
        """Score texts in advance (startup pre-warm). Returns how many were newly scored."""
        fresh = 0
        for text in texts:
            if self.cache.get(text) is None and self.model_available:
                self.score(text)
                fresh += 1
        return fresh
