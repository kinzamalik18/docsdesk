from pathlib import Path

import pytest

from app.chunking import chunk_document, embedding_text
from app.llm.fake import FakeProvider
from app.loaders import load_directory
from app.retrieval import retrieve, top_similarity
from app.store.memory import MemoryStore

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_docs" / "fernbill"


@pytest.fixture(scope="module")
def indexed():
    llm = FakeProvider(dim=256)
    store = MemoryStore()
    for doc in load_directory(SAMPLE_DIR):
        chunks = chunk_document(doc)
        vectors = llm.embed_documents([embedding_text(c) for c in chunks])
        for chunk, vector in zip(chunks, vectors):
            chunk.embedding = vector
        store.replace_document(doc.doc_id, doc.title, doc.source, chunks)
    return store, llm


@pytest.mark.parametrize(
    "question, expected_doc",
    [
        ("How much does the Growth plan cost per month?", "plans-and-pricing"),
        ("Can I connect Xero?", "integrations"),
        ("Do you support SMS codes for two-factor authentication?", "security"),
        ("How long is the export download link valid?", "data-export-and-deletion"),
    ],
)
def test_expected_document_is_retrieved(indexed, question, expected_doc):
    store, llm = indexed
    results = retrieve(question, store, llm, k=5)
    assert expected_doc in {r.chunk.doc_id for r in results}


def test_results_are_ranked_and_limited(indexed):
    store, llm = indexed
    results = retrieve("refund annual subscription", store, llm, k=3)
    assert len(results) == 3
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_keyword_only_hits_have_zero_similarity(indexed):
    store, llm = indexed
    results = retrieve("Xero", store, llm, k=10)
    assert top_similarity(results) > 0
    assert all(r.similarity >= 0 for r in results)


def test_empty_store_returns_nothing():
    assert retrieve("anything", MemoryStore(), FakeProvider(dim=64)) == []


def test_replace_document_overwrites_old_chunks(indexed):
    store, _ = indexed
    before = store.chunk_count()
    store.replace_document("security", "Security", "security.md", [])
    assert store.chunk_count() < before
    assert "security" not in {s.doc_id for s in store.list_sources()}
