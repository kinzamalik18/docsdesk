from dataclasses import dataclass, field

from pydantic import BaseModel, Field


@dataclass
class Document:
    doc_id: str
    title: str
    text: str
    source: str  # file name the document came from


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    section: str
    text: str
    position: int
    embedding: list[float] | None = field(default=None, repr=False)


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float  # fused retrieval score, only meaningful for ranking
    similarity: float  # cosine similarity to the question, 0 if found by keyword only


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class Citation(BaseModel):
    number: int
    doc_id: str
    doc_title: str
    section: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    answered: bool
    citations: list[Citation]
    top_similarity: float


class FeedbackRequest(BaseModel):
    question: str = Field(max_length=1000)
    answer: str = Field(max_length=5000)
    helpful: bool


class GapItem(BaseModel):
    question: str
    top_similarity: float
    reason: str
    created_at: str


class SourceDoc(BaseModel):
    doc_id: str
    title: str
    chunks: int
