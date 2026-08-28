import math
import os
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv
from openai import OpenAI


EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_TIMEOUT_SECONDS = 30.0
PROJECT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def create_embedding_client() -> OpenAI:
    """Create the shared OpenAI client used for course embeddings."""
    load_dotenv(PROJECT_ENV_FILE)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(
        api_key=api_key,
        timeout=EMBEDDING_TIMEOUT_SECONDS,
        max_retries=2,
    )


def embed_texts(
    texts: Sequence[str],
    *,
    client: Any | None = None,
) -> list[list[float]]:
    """Embed non-empty texts and validate the model's vector contract."""
    normalized = [text.strip() for text in texts]
    if not normalized:
        raise ValueError("at least one text is required")
    if any(not text for text in normalized):
        raise ValueError("embedding input cannot be empty")

    embedding_client = client or create_embedding_client()
    response = embedding_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=normalized,
        dimensions=EMBEDDING_DIMENSIONS,
        encoding_format="float",
    )
    items = sorted(response.data, key=lambda item: item.index)
    if len(items) != len(normalized):
        raise RuntimeError(
            f"expected {len(normalized)} embeddings, received {len(items)}"
        )

    vectors: list[list[float]] = []
    for item in items:
        vector = [float(value) for value in item.embedding]
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"expected {EMBEDDING_DIMENSIONS} dimensions, received {len(vector)}"
            )
        if not all(math.isfinite(value) for value in vector):
            raise RuntimeError("embedding contains a non-finite value")
        vectors.append(vector)
    return vectors


__all__ = [
    "EMBEDDING_DIMENSIONS",
    "EMBEDDING_MODEL",
    "create_embedding_client",
    "embed_texts",
]
