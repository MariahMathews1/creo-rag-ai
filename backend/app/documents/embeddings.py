from hashlib import sha256
import math
import re
from typing import Protocol

import httpx

from app.core.config import Settings


class EmbeddingProvider(Protocol):
    name: str
    model: str
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class MockEmbeddingProvider:
    name = "mock"
    model = "deterministic-hash-v1"
    dimensions = 96

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in re.findall(r"[A-Za-z0-9.]+", text.lower()):
                digest = sha256(token.encode()).digest()
                index = int.from_bytes(digest[:2], "big") % self.dimensions
                vector[index] += 1.0
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


class OpenAICompatibleEmbeddingProvider:
    name = "openai_compatible"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.openai_embedding_model
        if not settings.openai_api_key or not self.model:
            raise ValueError("OpenAI-compatible embeddings require an API key and model.")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}
        last_error: Exception | None = None
        for _ in range(3):
            try:
                with httpx.Client(timeout=30) as client:
                    response = client.post(
                        f"{self.settings.openai_base_url.rstrip('/')}/embeddings",
                        headers=headers, json={"model": self.model, "input": texts},
                    )
                    response.raise_for_status()
                    return [item["embedding"] for item in response.json()["data"]]
            except Exception as exc:
                last_error = exc
        raise RuntimeError("Embedding request failed after retries.") from last_error


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "mock":
        return MockEmbeddingProvider()
    return OpenAICompatibleEmbeddingProvider(settings)

