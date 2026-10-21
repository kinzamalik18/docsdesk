"""Split documents into chunks that follow the document's own structure.

Markdown is split at headings so each chunk is one section, with the heading
path kept as metadata. Long sections, and documents without headings, are
split at paragraph boundaries with one paragraph of overlap so that a sentence
that depends on the previous paragraph still has its context.
"""

import re

from app.models import Chunk, Document

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _sections(text: str) -> list[tuple[str, str]]:
    """Return (heading path, body) pairs. Text before the first heading gets an empty path."""
    sections: list[tuple[str, str]] = []
    path: list[tuple[int, str]] = []
    body: list[str] = []

    def flush() -> None:
        content = "\n".join(body).strip()
        if content:
            # Skip the document title (level 1) in the path, it is stored as doc_title.
            names = [name for level, name in path if level > 1]
            sections.append((" > ".join(names), content))

    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            flush()
            body = []
            level = len(match.group(1))
            path = [(lvl, name) for lvl, name in path if lvl < level]
            path.append((level, match.group(2)))
        else:
            body.append(line)
    flush()
    return sections


def _paragraph_windows(text: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    windows: list[str] = []
    current: list[str] = []
    for para in paragraphs:
        candidate = "\n\n".join(current + [para])
        if current and len(candidate) > max_chars:
            windows.append("\n\n".join(current))
            # Carry the last paragraph over as overlap, unless it alone is too big.
            overlap = current[-1] if len(current[-1]) + len(para) <= max_chars else None
            current = [overlap, para] if overlap else [para]
        else:
            current.append(para)
    if current:
        windows.append("\n\n".join(current))
    return windows


def chunk_document(doc: Document, max_chars: int = 1200) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section, body in _sections(doc.text):
        for piece in _paragraph_windows(body, max_chars):
            position = len(chunks)
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}#{position}",
                    doc_id=doc.doc_id,
                    doc_title=doc.title,
                    section=section,
                    text=piece,
                    position=position,
                )
            )
    return chunks


def embedding_text(chunk: Chunk) -> str:
    """Text sent to the embedding model. Adding the title and section helps short chunks."""
    header = chunk.doc_title if not chunk.section else f"{chunk.doc_title} > {chunk.section}"
    return f"{header}\n\n{chunk.text}"
