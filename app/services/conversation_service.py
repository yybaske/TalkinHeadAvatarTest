from app.repositories.conversation_feature_repository import (
    initialize_conversation_features,
)
from app.repositories.conversation_repository import (
    conversation_exists,
    create_conversation,
    delete_conversation,
    get_conversation_history,
    get_conversation_messages,
    list_conversations,
    save_message,
)


DEFAULT_HISTORY_LIMIT = 20


def _normalize_conversation_id(
    conversation_id,
) -> str | None:
    """
    UUID型でも文字列型でも受け取れるようにし、
    内部では必ずstrとして扱う。
    """

    if conversation_id is None:
        return None

    value = str(
        conversation_id
    ).strip()

    if not value:
        return None

    return value


def prepare_conversation(
    conversation_id=None,
) -> tuple[str, list[dict]]:
    normalized_id = (
        _normalize_conversation_id(
            conversation_id
        )
    )

    # =========================================================
    # 新規会話
    # =========================================================

    if not normalized_id:
        new_id = create_conversation()

        new_id = str(
            new_id
        )

        initialize_conversation_features(
            new_id
        )

        return (
            new_id,
            [],
        )

    # =========================================================
    # 既存会話
    # =========================================================

    if not conversation_exists(
        normalized_id
    ):
        raise ValueError(
            "指定されたconversation_idは"
            "存在しません。"
        )

    # 古い会話にもFeatureを補完する
    initialize_conversation_features(
        normalized_id
    )

    history = get_conversation_history(
        normalized_id,
        limit=DEFAULT_HISTORY_LIMIT,
    )

    return (
        normalized_id,
        history,
    )


def save_chat_result(
    conversation_id,
    query: str,
    result: dict,
) -> None:
    normalized_id = (
        _normalize_conversation_id(
            conversation_id
        )
    )

    if not normalized_id:
        raise ValueError(
            "conversation_idが"
            "指定されていません。"
        )

    save_message(
        conversation_id=(
            normalized_id
        ),
        role="user",
        content=query,
    )

    metadata = {
        "mode": result.get(
            "mode"
        ),
        "retrieval_used": result.get(
            "retrieval_used"
        ),
        "answerable": result.get(
            "answerable"
        ),
        "confidence": result.get(
            "confidence"
        ),
        "search_query": result.get(
            "search_query"
        ),
        "sources": result.get(
            "sources",
            [],
        ),
        "features": result.get(
            "features",
            {},
        ),
        "tool_calls": result.get(
            "tool_calls",
            [],
        ),
    }

    save_message(
        conversation_id=(
            normalized_id
        ),
        role="assistant",
        content=result[
            "answer"
        ],
        metadata=metadata,
    )


def get_conversation_list() -> dict:
    conversations = (
        list_conversations()
    )

    return {
        "status": "ok",
        "count": len(
            conversations
        ),
        "conversations": (
            conversations
        ),
    }


def get_conversation(
    conversation_id,
) -> dict:
    normalized_id = (
        _normalize_conversation_id(
            conversation_id
        )
    )

    if not normalized_id:
        raise ValueError(
            "conversation_idが"
            "指定されていません。"
        )

    if not conversation_exists(
        normalized_id
    ):
        raise ValueError(
            "指定されたconversation_idは"
            "存在しません。"
        )

    messages = (
        get_conversation_messages(
            normalized_id
        )
    )

    return {
        "status": "ok",
        "conversation_id": (
            normalized_id
        ),
        "message_count": len(
            messages
        ),
        "messages": messages,
    }


def remove_conversation(
    conversation_id,
) -> dict:
    normalized_id = (
        _normalize_conversation_id(
            conversation_id
        )
    )

    if not normalized_id:
        raise ValueError(
            "conversation_idが"
            "指定されていません。"
        )

    deleted = delete_conversation(
        normalized_id
    )

    if not deleted:
        raise ValueError(
            "指定されたconversation_idは"
            "存在しません。"
        )

    return {
        "status": "ok",
        "conversation_id": (
            normalized_id
        ),
        "message": (
            "会話を削除しました。"
        ),
    }