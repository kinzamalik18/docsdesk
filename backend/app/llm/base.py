from typing import Protocol

import numpy as np


class LLMProvider(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...

    def generate_json(self, system: str, prompt: str) -> str:
        """Return the model's raw text, which should be a JSON object."""
        ...


def normalize(vector: list[float]) -> list[float]:
    """Scale to unit length so a dot product equals cosine similarity."""
    arr = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm == 0:
        return arr.tolist()
    return (arr / norm).tolist()
