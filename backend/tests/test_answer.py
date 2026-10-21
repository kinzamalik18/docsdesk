import json

import pytest

from app.answer import answer_question, build_prompt, parse_model_output
from app.llm.fake import FakeProvider
from app.models import Chunk
from app.store.memory import MemoryStore


class ScriptedLLM(FakeProvider):
    """Fake embeddings, but a canned model reply so each branch can be tested."""

    def __init__(self, reply: str):
        super().__init__(dim=128)
        self.reply = reply
        self.calls = 0

    def generate_json(self, system: str, prompt: str) -> str:
        self.calls += 1
        return self.reply


def make_store(llm) -> MemoryStore:
    store = MemoryStore()
    texts = [
        ("pricing", "Plans", "Growth", "The Growth plan costs $24 per month and allows up to 3 users."),
        ("security", "Security", "2FA", "Two-factor authentication supports authenticator apps. SMS codes are not supported."),
    ]
    for i, (doc_id, title, section, text) in enumerate(texts):
        chunk = Chunk(chunk_id=f"{doc_id}#0", doc_id=doc_id, doc_title=title, section=section, text=text, position=0)
        chunk.embedding = llm.embed_documents([f"{title} {section} {text}"])[0]
        store.replace_document(doc_id, title, f"{doc_id}.md", [chunk])
    return store


def ask(llm, question, **kwargs):
    store = make_store(llm)
    response, _ = answer_question(question, store, llm, company="Fernbill", min_similarity=0.1, **kwargs)
    return response, store


def test_answer_with_valid_citation():
    llm = ScriptedLLM(json.dumps({"answerable": True, "answer": "It costs $24 per month [1].", "citations": [1]}))
    response, store = ask(llm, "How much is the Growth plan per month?")

    assert response.answered
    assert response.citations[0].doc_id == "pricing"
    assert store.list_gaps() == []


def test_model_saying_not_answerable_is_logged_as_gap():
    llm = ScriptedLLM(json.dumps({"answerable": False, "answer": "", "citations": []}))
    response, store = ask(llm, "What is the Growth plan price in yen?")

    assert not response.answered
    assert "couldn't find" in response.answer
    assert store.list_gaps()[0].reason == "model_said_not_in_docs"


def test_answer_without_citation_is_rejected():
    llm = ScriptedLLM(json.dumps({"answerable": True, "answer": "It costs $24.", "citations": []}))
    response, store = ask(llm, "How much is the Growth plan?")

    assert not response.answered
    assert store.list_gaps()[0].reason == "no_citation"


def test_out_of_range_citation_is_ignored():
    llm = ScriptedLLM(json.dumps({"answerable": True, "answer": "Yes [7].", "citations": [7]}))
    response, _ = ask(llm, "Growth plan price?")
    assert not response.answered


def test_low_similarity_skips_the_model():
    llm = ScriptedLLM("should not be called")
    store = make_store(llm)
    response, _ = answer_question("zebra migration patterns", store, llm, company="Fernbill", min_similarity=0.5)

    assert not response.answered
    assert llm.calls == 0
    assert store.list_gaps()[0].reason == "no_close_match"


def test_non_json_output_is_handled():
    llm = ScriptedLLM("Sure! The answer is 24 dollars.")
    response, store = ask(llm, "Growth plan price?")
    assert not response.answered
    assert store.list_gaps()[0].reason == "bad_model_output"


def test_log_gaps_can_be_turned_off():
    llm = ScriptedLLM(json.dumps({"answerable": False}))
    _, store = ask(llm, "Growth plan price?", log_gaps=False)
    assert store.list_gaps() == []


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ("[1, 2]", None),
        ("not json", None),
    ],
)
def test_parse_model_output(raw, expected):
    assert parse_model_output(raw) == expected


def test_prompt_numbers_sources_with_headings():
    llm = FakeProvider(dim=64)
    store = make_store(llm)
    from app.retrieval import retrieve

    prompt = build_prompt("price", retrieve("Growth price", store, llm, k=2))
    assert "[1] " in prompt and "Question: price" in prompt
