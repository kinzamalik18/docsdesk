"""Run a fixed question set through the real pipeline and score it.

Answerable questions are scored on three things:
- retrieval hit: an expected document was among the retrieved chunks
- citation hit: the answer cited an expected document
- fact match: every expected fact string appears in the answer

Unanswerable questions (no expected documents) pass only if the bot declines.
The scores are simple string checks, not a judge model, so they are cheap to
run and easy to audit, but they can miss a correct answer that is phrased
differently. Every row is kept in the report so results can be checked by hand.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.answer import answer_question
from app.config import Settings
from app.llm.base import LLMProvider
from app.store.base import Store

log = logging.getLogger(__name__)

EVAL_FILE = Path(__file__).resolve().parents[1] / "evals" / "fernbill.jsonl"


def load_eval_set(path: Path = EVAL_FILE) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _pct(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 1) if denominator else None


def score_item(item: dict, response, retrieved) -> dict:
    expected = set(item["expected_docs"])
    retrieved_docs = {r.chunk.doc_id for r in retrieved}
    cited_docs = {c.doc_id for c in response.citations}
    answer = response.answer.lower()
    row = {
        "id": item["id"],
        "question": item["question"],
        "answerable": bool(expected),
        "answered": response.answered,
        "answer": response.answer,
        "cited_docs": sorted(cited_docs),
        "top_similarity": response.top_similarity,
    }
    if expected:
        row["retrieval_hit"] = bool(expected & retrieved_docs)
        row["citation_hit"] = response.answered and bool(expected & cited_docs)
        row["fact_match"] = response.answered and all(f.lower() in answer for f in item["facts"])
        row["passed"] = row["citation_hit"] and row["fact_match"]
    else:
        row["passed"] = not response.answered
    return row


def summarize(rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    return {
        "total": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "answerable": len(answerable),
        "unanswerable": len(unanswerable),
        "answer_rate": _pct(sum(r["answered"] for r in answerable), len(answerable)),
        "retrieval_hit_rate": _pct(sum(r["retrieval_hit"] for r in answerable), len(answerable)),
        "citation_accuracy": _pct(sum(r["citation_hit"] for r in answerable), len(answerable)),
        "fact_match_rate": _pct(sum(r["fact_match"] for r in answerable), len(answerable)),
        "correct_refusal_rate": _pct(sum(r["passed"] for r in unanswerable), len(unanswerable)),
    }


@dataclass
class EvalStatus:
    state: str = "idle"  # idle, running, done, failed
    done: int = 0
    total: int = 0
    error: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def as_dict(self) -> dict:
        return {"state": self.state, "done": self.done, "total": self.total, "error": self.error}


def run_eval(store: Store, llm: LLMProvider, settings: Settings, status: EvalStatus, delay: float = 0.0) -> dict:
    items = load_eval_set()
    status.state, status.done, status.total, status.error = "running", 0, len(items), ""
    rows = []
    started = time.time()
    for item in items:
        response, retrieved = answer_question(
            item["question"],
            store,
            llm,
            company=settings.company_name,
            top_k=settings.top_k,
            min_similarity=settings.min_similarity,
            log_gaps=False,
        )
        rows.append(score_item(item, response, retrieved))
        status.done += 1
        if delay:
            time.sleep(delay)  # stay under free-tier rate limits

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - started, 1),
        "provider": llm.name,
        "chat_model": settings.gemini_chat_model if llm.name == "gemini" else llm.name,
        "embed_model": settings.gemini_embed_model if llm.name == "gemini" else llm.name,
        "top_k": settings.top_k,
        "min_similarity": settings.min_similarity,
        "summary": summarize(rows),
        "rows": rows,
    }
    store.save_eval_report(report)
    status.state = "done"
    return report


def start_eval_in_background(store: Store, llm: LLMProvider, settings: Settings, status: EvalStatus, delay: float) -> bool:
    """Returns False if an eval is already running."""
    with status.lock:
        if status.state == "running":
            return False
        status.state = "running"

    def worker() -> None:
        try:
            run_eval(store, llm, settings, status, delay)
        except Exception as exc:  # report the failure to the UI instead of dying silently
            log.exception("Eval failed")
            status.state, status.error = "failed", str(exc)[:300]

    threading.Thread(target=worker, daemon=True).start()
    return True
