from app.repositories.document_repository import (
    get_connection,
)


def list_conversation_features(
    conversation_id: str,
) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ff.feature_key,
                    ff.display_name,
                    ff.description,
                    ff.category,
                    ff.enabled AS globally_enabled,
                    COALESCE(
                        cf.enabled,
                        FALSE
                    ) AS conversation_enabled,
                    ff.sort_order
                FROM feature_flags ff

                LEFT JOIN conversation_features cf
                    ON cf.feature_key = ff.feature_key
                    AND cf.conversation_id = %s

                ORDER BY
                    ff.sort_order ASC,
                    ff.feature_key ASC
                """,
                (
                    conversation_id,
                ),
            )

            rows = cur.fetchall()

    return [
        {
            "feature_key": row[0],
            "display_name": row[1],
            "description": row[2],
            "category": row[3],
            "globally_enabled": row[4],
            "conversation_enabled": row[5],
            "sort_order": row[6],
        }
        for row in rows
    ]


def get_conversation_feature(
    conversation_id: str,
    feature_key: str,
) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ff.feature_key,
                    ff.display_name,
                    ff.description,
                    ff.category,
                    ff.enabled AS globally_enabled,
                    COALESCE(
                        cf.enabled,
                        FALSE
                    ) AS conversation_enabled,
                    ff.sort_order
                FROM feature_flags ff

                LEFT JOIN conversation_features cf
                    ON cf.feature_key = ff.feature_key
                    AND cf.conversation_id = %s

                WHERE
                    ff.feature_key = %s
                """,
                (
                    conversation_id,
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
        "globally_enabled": row[4],
        "conversation_enabled": row[5],
        "sort_order": row[6],
    }


def set_conversation_feature(
    conversation_id: str,
    feature_key: str,
    enabled: bool,
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversation_features (
                    conversation_id,
                    feature_key,
                    enabled,
                    updated_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    NOW()
                )

                ON CONFLICT (
                    conversation_id,
                    feature_key
                )
                DO UPDATE SET
                    enabled = EXCLUDED.enabled,
                    updated_at = NOW()

                RETURNING
                    conversation_id,
                    feature_key,
                    enabled,
                    updated_at
                """,
                (
                    conversation_id,
                    feature_key,
                    enabled,
                ),
            )

            row = cur.fetchone()

        conn.commit()

    return {
        "conversation_id": str(
            row[0]
        ),
        "feature_key": row[1],
        "enabled": row[2],
        "updated_at": row[3],
    }


def is_conversation_feature_enabled(
    conversation_id: str,
    feature_key: str,
) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    CASE
                        WHEN ff.enabled = TRUE
                            AND cf.enabled = TRUE
                        THEN TRUE
                        ELSE FALSE
                    END
                FROM feature_flags ff

                LEFT JOIN conversation_features cf
                    ON cf.feature_key = ff.feature_key
                    AND cf.conversation_id = %s

                WHERE
                    ff.feature_key = %s
                """,
                (
                    conversation_id,
                    feature_key,
                ),
            )

            row = cur.fetchone()

    if row is None:
        return False

    return bool(
        row[0]
    )


def initialize_conversation_features(
    conversation_id: str,
) -> None:
    """
    会話作成時の初期値。

    現時点では local_rag のみ
    デフォルトONとする。

    ただし管理者設定側でOFFなら
    ONにはしない。
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversation_features (
                    conversation_id,
                    feature_key,
                    enabled,
                    updated_at
                )

                SELECT
                    %s,
                    feature_key,

                    CASE
                        WHEN feature_key = 'local_rag'
                            AND enabled = TRUE
                        THEN TRUE
                        ELSE FALSE
                    END,

                    NOW()

                FROM feature_flags

                ON CONFLICT (
                    conversation_id,
                    feature_key
                )
                DO NOTHING
                """,
                (
                    conversation_id,
                ),
            )

        conn.commit()


def disable_conversation_feature_for_all(
    feature_key: str,
) -> int:
    """
    管理者側で機能をOFFにした場合に、
    会話側の設定もOFFへ寄せたい場合に使用できる。

    現状は必須ではないが、
    将来の管理処理用に用意しておく。
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE conversation_features
                SET
                    enabled = FALSE,
                    updated_at = NOW()
                WHERE
                    feature_key = %s
                    AND enabled = TRUE
                """,
                (
                    feature_key,
                ),
            )

            updated_count = (
                cur.rowcount
            )

        conn.commit()

    return updated_count