import psycopg

from app.core.config import settings


RRF_K = 60


def get_connection():
    return psycopg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )


def check_connection():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT version();"
            )

            return cur.fetchone()[0]


def list_documents() -> list[dict]:
    """
    登録済み文書の一覧を取得する。
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.id,
                    d.filename,
                    d.content_type,
                    d.created_at,
                    COUNT(dc.id) AS chunk_count
                FROM documents d
                LEFT JOIN document_chunks dc
                    ON dc.document_id = d.id
                GROUP BY
                    d.id,
                    d.filename,
                    d.content_type,
                    d.created_at
                ORDER BY
                    d.created_at DESC,
                    d.id DESC
                """
            )

            rows = cur.fetchall()

    return [
        {
            "document_id": row[0],
            "filename": row[1],
            "content_type": row[2],
            "created_at": row[3],
            "chunk_count": row[4],
        }
        for row in rows
    ]


def delete_document(
    document_id: int,
) -> bool:
    """
    文書を削除する。

    document_chunks は
    ON DELETE CASCADE により自動削除される。
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM documents
                WHERE id = %s
                RETURNING id
                """,
                (
                    document_id,
                ),
            )

            deleted = cur.fetchone()

        conn.commit()

    return deleted is not None


def save_document(
    filename: str,
    content_type: str | None,
    chunks: list[dict],
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

            document_id = (
                cur.fetchone()[0]
            )

            for chunk, embedding in zip(
                chunks,
                embeddings,
            ):
                cur.execute(
                    """
                    INSERT INTO document_chunks (
                        document_id,
                        chunk_index,
                        content,
                        embedding,
                        page_number,
                        section_title
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s::vector,
                        %s,
                        %s
                    )
                    """,
                    (
                        document_id,
                        chunk["chunk_index"],
                        chunk["content"],
                        _vector_to_string(
                            embedding
                        ),
                        chunk.get(
                            "page_number"
                        ),
                        chunk.get(
                            "section_title"
                        ),
                    ),
                )

        conn.commit()

    return document_id


def search_similar_chunks(
    embedding: list[float],
    limit: int = 20,
) -> list[dict]:
    vector = _vector_to_string(
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
                    dc.page_number,
                    dc.section_title,
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
                    vector,
                    vector,
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
            "page_number": row[5],
            "section_title": row[6],
            "distance": float(
                row[7]
            ),
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
                    dc.page_number,
                    dc.section_title,
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
                ORDER BY
                    lexical_score DESC
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
            "page_number": row[5],
            "section_title": row[6],
            "lexical_score": float(
                row[7]
            ),
        }
        for row in rows
    ]


def hybrid_search(
    query: str,
    embedding: list[float],
    limit: int = 20,
    candidate_limit: int = 30,
) -> list[dict]:
    vector_results = search_similar_chunks(
        embedding,
        candidate_limit,
    )

    keyword_results = search_keyword_chunks(
        query,
        candidate_limit,
    )

    combined = {}

    for rank, result in enumerate(
        vector_results,
        start=1,
    ):
        chunk_id = result[
            "chunk_id"
        ]

        combined[chunk_id] = {
            **result,
            "vector_rank": rank,
            "keyword_rank": None,
            "lexical_score": None,
            "rrf_score": (
                1.0
                / (RRF_K + rank)
            ),
        }

    for rank, result in enumerate(
        keyword_results,
        start=1,
    ):
        chunk_id = result[
            "chunk_id"
        ]

        if chunk_id not in combined:
            combined[chunk_id] = {
                **result,
                "vector_rank": None,
                "keyword_rank": rank,
                "distance": None,
                "rrf_score": 0.0,
            }

        combined[
            chunk_id
        ][
            "keyword_rank"
        ] = rank

        combined[
            chunk_id
        ][
            "lexical_score"
        ] = result[
            "lexical_score"
        ]

        combined[
            chunk_id
        ][
            "rrf_score"
        ] += (
            1.0
            / (RRF_K + rank)
        )

    results = sorted(
        combined.values(),
        key=lambda item: item[
            "rrf_score"
        ],
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