from app.core.config import settings
from app.core.openai_client import client


def create_embedding(
    text: str,
) -> list[float]:
    if not text.strip():
        raise ValueError(
            "Embedding対象のテキストが空です。"
        )

    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
    )

    return response.data[
        0
    ].embedding


def create_embeddings(
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        return []

    cleaned = []

    for text in texts:
        if not text.strip():
            raise ValueError(
                "Embedding対象に空文字が含まれています。"
            )

        cleaned.append(text)

    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=cleaned,
    )

    return [
        item.embedding
        for item in response.data
    ]