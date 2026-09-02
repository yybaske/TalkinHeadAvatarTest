from app.repositories.document_repository import (
    get_connection,
)


def get_user_by_username(
    username: str,
) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    display_name,
                    role,
                    enabled,
                    created_at,
                    updated_at
                FROM users
                WHERE
                    LOWER(username)
                    =
                    LOWER(%s)
                """,
                (
                    username,
                ),
            )

            row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
        "display_name": row[3],
        "role": row[4],
        "enabled": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


def get_user_by_id(
    user_id: int,
) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    display_name,
                    role,
                    enabled,
                    created_at,
                    updated_at
                FROM users
                WHERE
                    id = %s
                """,
                (
                    user_id,
                ),
            )

            row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
        "display_name": row[3],
        "role": row[4],
        "enabled": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


def create_user(
    username: str,
    password_hash: str,
    display_name: str | None = None,
    role: str = "user",
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    display_name,
                    role,
                    enabled,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    TRUE,
                    NOW(),
                    NOW()
                )
                RETURNING
                    id,
                    username,
                    display_name,
                    role,
                    enabled,
                    created_at,
                    updated_at
                """,
                (
                    username,
                    password_hash,
                    display_name,
                    role,
                ),
            )

            row = cur.fetchone()

        conn.commit()

    return {
        "id": row[0],
        "username": row[1],
        "display_name": row[2],
        "role": row[3],
        "enabled": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


def count_users() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)
                FROM users
                """
            )

            row = cur.fetchone()

    return int(
        row[0]
    )