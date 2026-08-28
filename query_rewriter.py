from openai import OpenAI


MODEL_NAME = "gpt-5.6-luna"

client = OpenAI()


def rewrite_query(
    query: str,
    history: list[dict] | None = None,
) -> str:
    """
    ユーザーの質問をRAG検索向けの英語検索クエリへ変換する。

    history 例:
    [
        {"role": "user", "content": "ServiceNow CSMについて教えて"},
        {"role": "assistant", "content": "ServiceNow CSMは..."}
    ]
    """

    if not query.strip():
        raise ValueError(
            "検索文字列が空です。"
        )

    conversation = []

    if history:
        for item in history:
            role = item.get("role", "").strip()
            content = item.get("content", "").strip()

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

    conversation.append(
        {
            "role": "user",
            "content": query,
        }
    )

    response = client.responses.create(
        model=MODEL_NAME,
        input=[
            {
                "role": "system",
                "content": (
                    "You rewrite the latest user question into a concise "
                    "English search query for document retrieval. "
                    "Use the conversation history to resolve references "
                    "such as 'this product', 'it', 'that feature', "
                    "'this function', and similar expressions. "
                    "The documents are mainly technical and business "
                    "documents written in English. "
                    "Preserve product names, technical terms, acronyms, "
                    "and proper nouns. "
                    "Do not answer the question. "
                    "Return only one rewritten search query."
                ),
            },
            *conversation,
        ],
    )

    rewritten = response.output_text.strip()

    if not rewritten:
        return query

    return rewritten