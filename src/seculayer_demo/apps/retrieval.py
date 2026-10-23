"""A small BM25 ranking over the knowledge-base articles (docs/PLAN.md §5.6)."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from seculayer_demo.scenarios import Article

K1 = 1.5
B = 0.75
_WORD = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
_STOP = {
    "a", "an", "and", "are", "at", "be", "can", "do", "for", "how", "i", "in", "is", "it",
    "my", "of", "on", "or", "the", "this", "to", "what", "when", "who", "with", "you", "your",
    "s", "what's",
}  # fmt: skip


def _stem(word: str) -> str:
    """A light stemmer: plural "s" only ("expenses" -> "expense", "resets" -> "reset")."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def tokens(text: str) -> list[str]:
    words = [part for w in _WORD.findall(text.lower()) for part in w.split("-")]
    return [_stem(w) for w in words if w not in _STOP]


def rank(query: str, articles: Sequence[Article], top_k: int = 3) -> list[Article]:
    """The top-k articles by BM25 over title and body. Ties keep the knowledge-base order."""
    docs = [tokens(f"{a.title} {a.title} {a.body}") for a in articles]
    if not docs:
        return []
    average = sum(len(d) for d in docs) / len(docs)
    frequency = Counter(term for doc in docs for term in set(doc))
    n = len(docs)
    scores = []
    for index, doc in enumerate(docs):
        counts = Counter(doc)
        score = 0.0
        for term in set(tokens(query)):
            if term not in counts:
                continue
            idf = math.log(1 + (n - frequency[term] + 0.5) / (frequency[term] + 0.5))
            tf = counts[term]
            score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * len(doc) / average))
        scores.append((score, -index))
    order = sorted(range(n), key=lambda i: scores[i], reverse=True)
    return [articles[i] for i in order[:top_k]]
