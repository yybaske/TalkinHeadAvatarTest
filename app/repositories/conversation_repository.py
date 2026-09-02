import uuid

from psycopg.types.json import Jsonb

from app.repositories.document_repository import (
    get_connection,
)


def create_conversation() -> str:
    conversation_id = str(
        uuid.uuid4()
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (
                    id
                )
                VALUES (
                    %s
                )
                """,
                (
                    conversation_id,
                ),
            )

        conn.commit()

    return conversation_id


def conversation_exists(
    conversation_id: str,
) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM conversations
                WHERE id = %s
                """,
                (
                    conversation_id,
                ),
            )

            row = cur.fetchone()

    return row is not None


def list_conversations() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.id,
                    c.created_at,
                    c.updated_at,
                    (
                        SELECT content
                        FROM conversation_messages cm
                        WHERE
                            cm.conversation_id = c.id
                            AND cm.role = 'user'
                        ORDER BY
                            cm.created_at ASC,
                            cm.id ASC
                        LIMIT 1
                    ) AS first_message,
                    (
                        SELECT COUNT(*)
                        FROM conversation_messages cm
                        WHERE
                            cm.conversation_id = c.id
                    ) AS message_count
                FROM conversations c
                ORDER BY
                    c.updated_at DESC,
                    c.created_at DESC
                """
            )

            rows = cur.fetchall()

    return [
        {
            "conversation_id": str(
                row[0]
            ),
            "created_at": row[1],
            "updated_at": row[2],
            "title": (
                row[3]
                or "新しいチャット"
            ),
            "message_count": row[4],
        }
        for row in rows
    ]


def get_conversation_history(
    conversation_id: str,
    limit: int = 20,
) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    role,
                    content
                FROM (
                    SELECT
                        id,
                        role,
                        content,
                        created_at
                    FROM conversation_messages
                    WHERE conversation_id = %s
                    ORDER BY
                        created_at DESC,
                        id DESC
                    LIMIT %s
                ) history
                ORDER BY
                    created_at ASC,
                    id ASC
                """,
                (
                    conversation_id,
                    limit,
                ),
            )

            rows = cur.fetchall()

    return [
        {
            "role": row[0],
            "content": row[1],
        }
        for row in rows
    ]


def get_conversation_messages(
    conversation_id: str,
) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    role,
                    content,
                    metadata,
                    created_at
                FROM conversation_messages
                WHERE conversation_id = %s
                ORDER BY
                    created_at ASC,
                    id ASC
                """,
                (
                    conversation_id,
                ),
            )

            rows = cur.fetchall()

    return [
        {
            "message_id": row[0],
            "role": row[1],
            "content": row[2],
            "metadata": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]


def save_message(
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> int:
    if role not in {
        "user",
        "assistant",
    }:
        raise ValueError(
            f"不正なroleです: {role}"
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversation_messages (
                    conversation_id,
                    role,
                    content,
                    metadata
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id
                """,
                (
                    conversation_id,
                    role,
                    content,
                    (
                        Jsonb(metadata)
                        if metadata is not None
                        else None
                    ),
                ),
            )

            message_id = (
                cur.fetchone()[0]
            )

            cur.execute(
                """
                UPDATE conversations
                SET updated_at = NOW()
                WHERE id = %s
                """,
                (
                    conversation_id,
                ),
            )

        conn.commit()

    return message_id


def delete_conversation(
    conversation_id: str,
) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM conversations
                WHERE id = %s
                RETURNING id
                """,
                (
                    conversation_id,
                ),
            )

            deleted = cur.fetchone()

        conn.commit()

    return deleted is not None