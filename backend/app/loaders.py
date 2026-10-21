"""Turn files into Documents. Supports Markdown, plain text and PDF."""

import io
import re
from pathlib import Path

from pypdf import PdfReader

from app.models import Document

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".pdf"}


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or "document"


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+)", line.strip())
        if match:
            return match.group(1).strip()
    return fallback


def _pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(p for p in pages if p)


def load_bytes(filename: str, data: bytes) -> Document:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {suffix or 'none'}")

    stem = Path(filename).stem
    fallback_title = stem.replace("-", " ").replace("_", " ").strip().capitalize()

    if suffix == ".pdf":
        text = _pdf_text(data)
        title = fallback_title
    else:
        text = data.decode("utf-8", errors="replace")
        title = _title_from_markdown(text, fallback_title)

    if not text.strip():
        raise ValueError(f"No text found in {filename}. Scanned PDFs need OCR first.")

    return Document(doc_id=slugify(stem), title=title, text=text, source=filename)


def load_directory(path: str | Path) -> list[Document]:
    root = Path(path)
    if not root.is_dir():
        raise FileNotFoundError(f"Docs folder not found: {root}")
    docs = []
    for file in sorted(root.iterdir()):
        if file.suffix.lower() in SUPPORTED_SUFFIXES and file.name.lower() != "readme.md":
            docs.append(load_bytes(file.name, file.read_bytes()))
    return docs
