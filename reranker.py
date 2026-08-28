import json

from openai import OpenAI


MODEL_NAME = "gpt-5.6-luna"

client = OpenAI()


def rerank_chunks(
    query: str,
    candidates: list[dict],
    limit: int = 5,
) -> list[dict]:
    """
    Hybrid Searchで取得した候補を、
    ユーザーの質問との関連性で並び替える。
    """

    if not candidates:
        return []

    candidate_data = []

    for candidate in candidates:
        candidate_data.append(
            {
                "chunk_id": candidate["chunk_id"],
                "filename": candidate["filename"],
                "content": candidate["content"][:1500],
            }
        )

    prompt = {
        "question": query,
        "candidates": candidate_data,
    }

    response = client.responses.create(
        model=MODEL_NAME,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a reranker for a RAG system. "
                    "Rank the document chunks by how useful they are "
                    "for answering the user's question. "
                    "Prefer chunks that directly contain information "
                    "needed to answer the question. "
                    "Do not prefer a chunk merely because it contains "
                    "the same product name. "
                    "Return JSON only in the following format: "
                    '{"chunk_ids":[1,2,3]} '
                    "Return no more chunk IDs than requested."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Return the best {limit} chunks.\n\n"
                    + json.dumps(
                        prompt,
                        ensure_ascii=False,
                    )
                ),
            },
        ],
    )

    try:
        result = json.loads(
            response.output_text.strip()
        )

        ranked_ids = result.get(
            "chunk_ids",
            [],
        )

    except (
        json.JSONDecodeError,
        AttributeError,
    ):
        # Reranker失敗時は
        # Hybrid Search結果をそのまま返す
        return candidates[:limit]

    candidate_map = {
        candidate["chunk_id"]: candidate
        for candidate in candidates
    }

    reranked = []

    for rank, chunk_id in enumerate(
        ranked_ids,
        start=1,
    ):
        if chunk_id not in candidate_map:
            continue

        item = dict(
            candidate_map[chunk_id]
        )

        item["rerank_rank"] = rank

        reranked.append(item)

        if len(reranked) >= limit:
            break

    # AIの返却件数が足りなかった場合の保険
    if len(reranked) < limit:
        selected_ids = {
            item["chunk_id"]
            for item in reranked
        }

        for candidate in candidates:
            if candidate["chunk_id"] in selected_ids:
                continue

            item = dict(candidate)

            item["rerank_rank"] = (
                len(reranked) + 1
            )

            reranked.append(item)

            if len(reranked) >= limit:
                break

    return reranked