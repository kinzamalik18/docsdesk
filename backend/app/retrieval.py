"""Hybrid retrieval: vector search and keyword search, fused by reciprocal rank.

Vector search finds paraphrases ("cancel my plan" vs "end subscription").
Keyword search catches exact terms embeddings can blur, like "2FA", "Xero" or
"INV-0001". Reciprocal rank fusion merges the two lists without having to
calibrate their very different score scales.
"""

from app.llm.base import LLMProvider
from app.models import ScoredChunk
from app.store.base import Store

RRF_K = 60  # standard constant from Cormack et al. (2009)


def retrieve(question: str, store: Store, llm: LLMProvider, k: int = 5) -> list[ScoredChunk]:
    query_vector = llm.embed_query(question)
    candidates = max(k * 4, 20)

    vector_hits = store.vector_search(query_vector, candidates)
    keyword_hits = store.keyword_search(question, candidates)

    fused: dict[str, ScoredChunk] = {}
    for rank, (chunk, similarity) in enumerate(vector_hits):
        fused[chunk.chunk_id] = ScoredChunk(chunk=chunk, score=1 / (RRF_K + rank + 1), similarity=similarity)
    for rank, (chunk, _) in enumerate(keyword_hits):
        if chunk.chunk_id in fused:
            fused[chunk.chunk_id].score += 1 / (RRF_K + rank + 1)
        else:
            fused[chunk.chunk_id] = ScoredChunk(chunk=chunk, score=1 / (RRF_K + rank + 1), similarity=0.0)

    ranked = sorted(fused.values(), key=lambda s: s.score, reverse=True)
    return ranked[:k]


def top_similarity(results: list[ScoredChunk]) -> float:
    return max((r.similarity for r in results), default=0.0)
