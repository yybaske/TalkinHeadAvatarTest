from app.repositories.document_repository import (
    get_connection,
)


def list_features() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    feature_key,
                    display_name,
                    description,
                    category,
                    enabled,
                    sort_order,
                    updated_at
                FROM feature_flags
                ORDER BY
                    sort_order ASC,
                    feature_key ASC
                """
            )

            rows = cur.fetchall()

    return [
        {
            "feature_key": row[0],
            "display_name": row[1],
            "description": row[2],
            "category": row[3],
            "enabled": row[4],
            "sort_order": row[5],
            "updated_at": row[6],
        }
        for row in rows
    ]


def get_feature(
    feature_key: str,
) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    feature_key,
                    display_name,
                    description,
                    category,
                    enabled,
                    sort_order,
                    updated_at
                FROM feature_flags
                WHERE feature_key = %s
                """,
                (
                    feature_key,
                ),
            )

            row = cur.fetchone()

    if row is None:
        return None

    return {
        "feature_key": row[0],
        "display_name": row[1],
        "description": row[2],
        "category": row[3],
        "enabled": row[4],
        "sort_order": row[5],
        "updated_at": row[6],
    }


def is_feature_enabled(
    feature_key: str,
) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT enabled
                FROM feature_flags
                WHERE feature_key = %s
                """,
                (
                    feature_key,
                ),
            )

            row = cur.fetchone()

    if row is None:
        return False

    return bool(
        row[0]
    )


def update_feature(
    feature_key: str,
    enabled: bool,
) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE feature_flags
                SET
                    enabled = %s,
                    updated_at = NOW()
                WHERE feature_key = %s
                RETURNING
                    feature_key,
                    display_name,
                    description,
                    category,
                    enabled,
                    sort_order,
                    updated_at
                """,
                (
                    enabled,
                    feature_key,
                ),
            )

            row = cur.fetchone()

        conn.commit()

    if row is None:
        return None

    return {
        "feature_key": row[0],
        "display_name": row[1],
        "description": row[2],
        "category": row[3],
        "enabled": row[4],
        "sort_order": row[5],
        "updated_at": row[6],
    }