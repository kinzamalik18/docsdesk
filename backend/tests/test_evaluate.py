from app.config import Settings
from app.evaluate import EvalStatus, load_eval_set, run_eval, summarize
from app.indexer import index_documents
from app.llm.fake import FakeProvider
from app.loaders import load_directory
from app.store.memory import MemoryStore

from tests.test_chunking import SAMPLE_DIR


def test_eval_set_is_well_formed():
    items = load_eval_set()
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)) == 32
    doc_ids = {d.doc_id for d in load_directory(SAMPLE_DIR)}
    for item in items:
        assert set(item["expected_docs"]) <= doc_ids, item["id"]
        if not item["expected_docs"]:
            assert item["facts"] == []


def test_run_eval_end_to_end_with_fake_model():
    settings = Settings(llm_provider="fake", min_similarity=0.2, embed_dim=256)
    llm = FakeProvider(dim=256)
    store = MemoryStore()
    index_documents(load_directory(SAMPLE_DIR), store, llm)
    status = EvalStatus()

    report = run_eval(store, llm, settings, status)

    assert status.state == "done" and status.done == 32
    assert report["summary"]["total"] == 32
    assert store.latest_eval_report() == report
    # The eval must not pollute the documentation gap list.
    assert store.list_gaps() == []


def test_summarize_counts():
    rows = [
        {"answerable": True, "answered": True, "retrieval_hit": True, "citation_hit": True, "fact_match": True, "passed": True},
        {"answerable": True, "answered": False, "retrieval_hit": True, "citation_hit": False, "fact_match": False, "passed": False},
        {"answerable": False, "answered": False, "passed": True},
    ]
    summary = summarize(rows)
    assert summary["passed"] == 2
    assert summary["answer_rate"] == 50.0
    assert summary["correct_refusal_rate"] == 100.0
