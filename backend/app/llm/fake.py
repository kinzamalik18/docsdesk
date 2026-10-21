"""Offline provider for tests and keyless demos.

Embeddings are hashed bags of words, so texts that share words end up close
together. That is enough to test retrieval and the answer pipeline without
calling any API. Answers just quote the first source. It is not a model.
"""

import hashlib
import json
import re

from app.llm.base import normalize

WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "does", "can", "i", "my", "to", "of", "in", "on",
    "for", "and", "or", "how", "what", "when", "it", "be", "with", "you", "your", "if",
}


def _tokens(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOPWORDS]


class FakeProvider:
    name = "fake"

    def __init__(self, dim: int = 768):
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in _tokens(text):
            digest = int(hashlib.md5(token.encode()).hexdigest(), 16)
            vector[digest % self.dim] += 1.0
        return normalize(vector)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def generate_json(self, system: str, prompt: str) -> str:
        match = re.search(r"\[1\][^\n]*\n(.+?)(?:\n\[2\]|\nQuestion:)", prompt, re.S)
        if not match:
            return json.dumps({"answerable": False, "answer": "", "citations": []})
        first_sentence = match.group(1).strip().split(". ")[0].rstrip(".")
        return json.dumps({"answerable": True, "answer": f"{first_sentence}. [1]", "citations": [1]})
