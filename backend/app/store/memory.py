"""In-memory store. Good for demos and tests. Everything is lost on restart."""

import math
import re
from collections import Counter
from datetime import datetime, timezone

import numpy as np

from app.models import Chunk, GapItem, SourceDoc

WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = {"a", "an", "the", "is", "are", "do", "does", "can", "i", "my", "to", "of", "in",
             "on", "for", "and", "or", "how", "what", "when", "it", "be", "with", "you", "your"}


def tokenize(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOPWORDS]


class MemoryStore:
    persistent = False

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._titles: dict[str, str] = {}
        self._gaps: list[GapItem] = []
        self._feedback: list[dict] = []
        self._eval: dict | None = None

    # Documents ---------------------------------------------------------------

    def replace_document(self, doc_id: str, title: str, source: str, chunks: list[Chunk]) -> None:
        self._chunks = [c for c in self._chunks if c.doc_id != doc_id] + chunks
        self._titles[doc_id] = title

    def delete_document(self, doc_id: str) -> bool:
        before = len(self._chunks)
        self._chunks = [c for c in self._chunks if c.doc_id != doc_id]
        self._titles.pop(doc_id, None)
        return len(self._chunks) < before

    def list_sources(self) -> list[SourceDoc]:
        counts = Counter(c.doc_id for c in self._chunks)
        return sorted(
            (SourceDoc(doc_id=d, title=self._titles.get(d, d), chunks=n) for d, n in counts.items()),
            key=lambda s: s.title,
        )

    def chunk_count(self) -> int:
        return len(self._chunks)

    # Search ------------------------------------------------------------------

    def vector_search(self, query_vector: list[float], k: int) -> list[tuple[Chunk, float]]:
        candidates = [c for c in self._chunks if c.embedding is not None]
        if not candidates:
            return []
        matrix = np.asarray([c.embedding for c in candidates], dtype=np.float32)
        scores = matrix @ np.asarray(query_vector, dtype=np.float32)
        order = np.argsort(-scores)[:k]
        return [(candidates[i], float(scores[i])) for i in order]

    def keyword_search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        """BM25 over chunk text plus title and section."""
        query_terms = set(tokenize(query))
        if not query_terms or not self._chunks:
            return []
        docs = [tokenize(f"{c.doc_title} {c.section} {c.text}") for c in self._chunks]
        avg_len = sum(len(d) for d in docs) / len(docs)
        n = len(docs)
        doc_freq = Counter(t for d in docs for t in set(d))
        k1, b = 1.5, 0.75

        scored = []
        for chunk, tokens in zip(self._chunks, docs):
            tf = Counter(tokens)
            score = 0.0
            for term in query_terms:
                if term not in tf:
                    continue
                idf = math.log(1 + (n - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
                denom = tf[term] + k1 * (1 - b + b * len(tokens) / avg_len)
                score += idf * tf[term] * (k1 + 1) / denom
            if score > 0:
                scored.append((chunk, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]

    # Gaps, feedback, eval -----------------------------------------------------

    def log_gap(self, question: str, top_similarity: float, reason: str) -> None:
        self._gaps.append(
            GapItem(
                question=question,
                top_similarity=round(top_similarity, 3),
                reason=reason,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )

    def list_gaps(self, limit: int = 100) -> list[GapItem]:
        return list(reversed(self._gaps))[:limit]

    def log_feedback(self, question: str, answer: str, helpful: bool) -> None:
        self._feedback.append({"question": question, "answer": answer, "helpful": helpful})

    def save_eval_report(self, report: dict) -> None:
        self._eval = report

    def latest_eval_report(self) -> dict | None:
        return self._eval
