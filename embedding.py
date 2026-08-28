from openai import OpenAI


MODEL_NAME = "text-embedding-3-small"

client = OpenAI()


def create_embedding(text: str) -> list[float]:
    if not text.strip():
        raise ValueError("Embedding対象のテキストが空です。")

    response = client.embeddings.create(
        model=MODEL_NAME,
        input=text,
    )

    return response.data[0].embedding


def create_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    cleaned_texts = []

    for text in texts:
        if not text.strip():
            raise ValueError(
                "Embedding対象に空のテキストが含まれています。"
            )

        cleaned_texts.append(text)

    response = client.embeddings.create(
        model=MODEL_NAME,
        input=cleaned_texts,
    )

    return [
        item.embedding
        for item in response.data
    ]