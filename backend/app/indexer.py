import logging

from app.chunking import chunk_document, embedding_text
from app.llm.base import LLMProvider
from app.models import Document
from app.store.base import Store

log = logging.getLogger(__name__)


def index_documents(docs: list[Document], store: Store, llm: LLMProvider, max_chars: int = 1200) -> int:
    """Chunk, embed and store documents. Returns the number of chunks written."""
    total = 0
    for doc in docs:
        chunks = chunk_document(doc, max_chars=max_chars)
        if not chunks:
            log.warning("Skipping %s: no text after chunking", doc.source)
            continue
        vectors = llm.embed_documents([embedding_text(c) for c in chunks])
        for chunk, vector in zip(chunks, vectors):
            chunk.embedding = vector
        store.replace_document(doc.doc_id, doc.title, doc.source, chunks)
        total += len(chunks)
        log.info("Indexed %s (%d chunks)", doc.source, len(chunks))
    return total
