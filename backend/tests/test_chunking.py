from pathlib import Path

import pytest

from app.chunking import chunk_document, embedding_text
from app.loaders import load_bytes, load_directory, slugify
from app.models import Document

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_docs" / "fernbill"


def test_markdown_sections_keep_heading_path():
    text = "# Title\n\nIntro text.\n\n## Billing\n\nPay monthly.\n\n### Refunds\n\nWithin 14 days."
    doc = Document(doc_id="t", title="Title", text=text, source="t.md")

    chunks = chunk_document(doc)

    assert [c.section for c in chunks] == ["", "Billing", "Billing > Refunds"]
    assert chunks[2].text == "Within 14 days."
    assert chunks[2].doc_title == "Title"


def test_long_section_is_split_with_overlap():
    paras = [f"Paragraph {i} " + "word " * 40 for i in range(6)]
    doc = Document(doc_id="long", title="Long", text="\n\n".join(paras), source="l.txt")

    chunks = chunk_document(doc, max_chars=500)

    assert len(chunks) > 1
    assert all(len(c.text) <= 500 for c in chunks)
    # The last paragraph of one chunk starts the next one.
    first_last_para = chunks[0].text.split("\n\n")[-1]
    assert chunks[1].text.startswith(first_last_para)


def test_chunk_ids_are_unique_and_ordered():
    docs = load_directory(SAMPLE_DIR)
    chunks = [c for d in docs for c in chunk_document(d)]

    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert len(docs) == 14


def test_embedding_text_includes_title_and_section():
    doc = Document(doc_id="d", title="Plans", text="## Starter\n\n$9 per month", source="d.md")
    chunk = chunk_document(doc)[0]

    assert embedding_text(chunk).startswith("Plans > Starter")


def test_loader_reads_markdown_title():
    doc = load_bytes("my-file.md", b"# Real Title\n\nBody")
    assert doc.title == "Real Title"
    assert doc.doc_id == "my-file"


def test_loader_rejects_unknown_types_and_empty_files():
    with pytest.raises(ValueError):
        load_bytes("image.png", b"...")
    with pytest.raises(ValueError):
        load_bytes("empty.txt", b"   ")


def test_slugify():
    assert slugify("Plans & Pricing (2026)") == "plans-pricing-2026"
