import os

from dotenv import load_dotenv
from openai import OpenAI


# ------------------------------------------
# .env 読み込み
# ------------------------------------------

load_dotenv()


# ------------------------------------------
# OpenAI
# ------------------------------------------

MODEL_NAME = "gpt-5.6-luna"

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY が設定されていません。"
    )


client = OpenAI(
    api_key=api_key,
)


def generate_answer(
    query: str,
    chunks: list[dict],
    history: list[dict] | None = None,
) -> str:
    """
    検索されたチャンクを根拠として、
    ユーザーの質問に日本語で回答する。
    """

    if not query.strip():
        raise ValueError(
            "質問が空です。"
        )

    if not chunks:
        return (
            "参照できる文書内に、"
            "質問へ回答するための十分な情報がありませんでした。"
        )

    # ------------------------------------------
    # 検索結果をコンテキスト化
    # ------------------------------------------

    context_parts = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        filename = chunk.get(
            "filename",
            "unknown",
        )

        chunk_index = chunk.get(
            "chunk_index",
        )

        content = chunk.get(
            "content",
            "",
        )

        context_parts.append(
            (
                f"[Source {index}]\n"
                f"Filename: {filename}\n"
                f"Chunk: {chunk_index}\n"
                f"Content:\n{content}"
            )
        )

    context_text = "\n\n".join(
        context_parts
    )

    # ------------------------------------------
    # 会話履歴
    # ------------------------------------------

    conversation = []

    if history:
        for item in history:
            role = item.get(
                "role",
                "",
            ).strip()

            content = item.get(
                "content",
                "",
            ).strip()

            if role not in {
                "user",
                "assistant",
            }:
                continue

            if not content:
                continue

            conversation.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    # ------------------------------------------
    # 回答生成
    # ------------------------------------------

    response = client.responses.create(
        model=MODEL_NAME,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a RAG assistant. "
                    "Answer the user's question in Japanese. "
                    "Use only the provided document sources "
                    "as factual evidence. "
                    "Do not invent information that is not "
                    "supported by the sources. "
                    "If the sources do not contain enough "
                    "information to answer the question, "
                    "clearly say so. "
                    "Answer naturally and concisely. "
                    "When making a factual statement based on "
                    "a source, cite it using [Source N]. "
                    "Multiple sources may be cited like "
                    "[Source 1][Source 3]. "
                    "Do not expose internal retrieval scores "
                    "or ranking information."
                ),
            },
            *conversation,
            {
                "role": "user",
                "content": (
                    f"Question:\n{query}\n\n"
                    f"Retrieved document sources:\n\n"
                    f"{context_text}"
                ),
            },
        ],
    )

    answer = response.output_text.strip()

    if not answer:
        return (
            "回答を生成できませんでした。"
        )

    return answer