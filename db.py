import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


RRF_K = 60


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def check_connection():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            return cur.fetchone()[0]


def save_document(
    filename: str,
    content_type: str | None,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError(
            "チャンク数とEmbedding数が一致しません。"
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (
                    filename,
                    content_type
                )
                VALUES (
                    %s,
                    %s
                )
                RETURNING id
                """,
                (
                    filename,
                    content_type,
                ),
            )

            document_id = cur.fetchone()[0]

            for index, (chunk, embedding) in enumerate(
                zip(chunks, embeddings)
            ):
                vector_string = _vector_to_string(
                    embedding
                )

                cur.execute(
                    """
                    INSERT INTO document_chunks (
                        document_id,
                        chunk_index,
                        content,
                        embedding
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s::vector
                    )
                    """,
                    (
                        document_id,
                        index,
                        chunk,
                        vector_string,
                    ),
                )

        conn.commit()

    return document_id


def search_similar_chunks(
    embedding: list[float],
    limit: int = 20,
) -> list[dict]:
    vector_string = _vector_to_string(
        embedding
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    dc.id,
                    dc.document_id,
                    dc.chunk_index,
                    dc.content,
                    d.filename,
                    dc.embedding <=> %s::vector
                        AS distance
                FROM document_chunks dc
                INNER JOIN documents d
                    ON d.id = dc.document_id
                WHERE dc.embedding IS NOT NULL
                ORDER BY
                    dc.embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    vector_string,
                    vector_string,
                    limit,
                ),
            )

            rows = cur.fetchall()

    return [
        {
            "chunk_id": row[0],
            "document_id": row[1],
            "chunk_index": row[2],
            "content": row[3],
            "filename": row[4],
            "distance": float(row[5]),
        }
        for row in rows
    ]


def search_keyword_chunks(
    query: str,
    limit: int = 20,
) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    dc.id,
                    dc.document_id,
                    dc.chunk_index,
                    dc.content,
                    d.filename,
                    word_similarity(
                        %s,
                        dc.content
                    ) AS lexical_score
                FROM document_chunks dc
                INNER JOIN documents d
                    ON d.id = dc.document_id
                WHERE
                    word_similarity(
                        %s,
                        dc.content
                    ) > 0
                ORDER BY lexical_score DESC
                LIMIT %s
                """,
                (
                    query,
                    query,
                    limit,
                ),
            )

            rows = cur.fetchall()

    return [
        {
            "chunk_id": row[0],
            "document_id": row[1],
            "chunk_index": row[2],
            "content": row[3],
            "filename": row[4],
            "lexical_score": float(row[5]),
        }
        for row in rows
    ]


def hybrid_search(
    query: str,
    embedding: list[float],
    limit: int = 5,
    candidate_limit: int = 20,
) -> list[dict]:
    vector_results = search_similar_chunks(
        embedding=embedding,
        limit=candidate_limit,
    )

    keyword_results = search_keyword_chunks(
        query=query,
        limit=candidate_limit,
    )

    combined = {}

    for rank, result in enumerate(
        vector_results,
        start=1,
    ):
        chunk_id = result["chunk_id"]

        if chunk_id not in combined:
            combined[chunk_id] = {
                **result,
                "vector_rank": None,
                "keyword_rank": None,
                "lexical_score": None,
                "rrf_score": 0.0,
            }

        combined[chunk_id]["vector_rank"] = rank
        combined[chunk_id]["distance"] = (
            result["distance"]
        )

        combined[chunk_id]["rrf_score"] += (
            1.0 / (RRF_K + rank)
        )

    for rank, result in enumerate(
        keyword_results,
        start=1,
    ):
        chunk_id = result["chunk_id"]

        if chunk_id not in combined:
            combined[chunk_id] = {
                **result,
                "vector_rank": None,
                "keyword_rank": None,
                "distance": None,
                "rrf_score": 0.0,
            }

        combined[chunk_id]["keyword_rank"] = rank
        combined[chunk_id]["lexical_score"] = (
            result["lexical_score"]
        )

        combined[chunk_id]["rrf_score"] += (
            1.0 / (RRF_K + rank)
        )

    results = sorted(
        combined.values(),
        key=lambda item: item["rrf_score"],
        reverse=True,
    )

    return results[:limit]


def _vector_to_string(
    embedding: list[float],
) -> str:
    return (
        "["
        + ",".join(
            str(value)
            for value in embedding
        )
        + "]"
    )