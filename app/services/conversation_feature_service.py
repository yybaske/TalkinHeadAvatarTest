from app.repositories.conversation_feature_repository import (
    get_conversation_feature,
    initialize_conversation_features,
    list_conversation_features,
    set_conversation_feature,
)
from app.repositories.feature_repository import (
    is_feature_enabled,
)


MCP_CHILD_FEATURES = {
    "mcp_servicenow",
    "mcp_aws",
    "mcp_github",
    "mcp_sharepoint",
}


def get_conversation_features(
    conversation_id: str,
) -> dict:
    initialize_conversation_features(
        conversation_id
    )

    features = (
        list_conversation_features(
            conversation_id
        )
    )

    return {
        "status": "ok",
        "conversation_id": (
            conversation_id
        ),
        "features": features,
    }


def update_conversation_feature(
    conversation_id: str,
    feature_key: str,
    enabled: bool,
) -> dict:
    feature = (
        get_conversation_feature(
            conversation_id,
            feature_key,
        )
    )

    if feature is None:
        raise ValueError(
            "指定された機能は存在しません。"
        )

    # =========================================================
    # 管理者設定チェック
    # =========================================================

    globally_enabled = (
        is_feature_enabled(
            feature_key
        )
    )

    if (
        enabled
        and not globally_enabled
    ):
        raise ValueError(
            "この機能は管理者設定で"
            "無効になっています。"
        )

    # =========================================================
    # MCP子機能
    #
    # ServiceNow / AWS / GitHub / SharePoint は
    # MCP自体が有効である必要がある。
    # =========================================================

    if (
        enabled
        and feature_key
        in MCP_CHILD_FEATURES
    ):
        mcp_globally_enabled = (
            is_feature_enabled(
                "mcp"
            )
        )

        if not mcp_globally_enabled:
            raise ValueError(
                "MCP連携が管理者設定で"
                "無効になっています。"
            )

        mcp_feature = (
            get_conversation_feature(
                conversation_id,
                "mcp",
            )
        )

        if (
            mcp_feature is None
            or not mcp_feature[
                "conversation_enabled"
            ]
        ):
            raise ValueError(
                "このチャットではMCP連携が"
                "無効です。先にMCP連携を"
                "有効にしてください。"
            )

    # =========================================================
    # MCPをOFFにした場合
    #
    # その会話のServiceNow/AWS等もOFF
    # =========================================================

    disabled_children = []

    if (
        feature_key == "mcp"
        and enabled is False
    ):
        for child_key in (
            MCP_CHILD_FEATURES
        ):
            child_feature = (
                get_conversation_feature(
                    conversation_id,
                    child_key,
                )
            )

            if (
                child_feature
                and child_feature[
                    "conversation_enabled"
                ]
            ):
                set_conversation_feature(
                    conversation_id=(
                        conversation_id
                    ),
                    feature_key=(
                        child_key
                    ),
                    enabled=False,
                )

                disabled_children.append(
                    child_key
                )

    updated = (
        set_conversation_feature(
            conversation_id=(
                conversation_id
            ),
            feature_key=feature_key,
            enabled=enabled,
        )
    )

    return {
        "status": "ok",
        "conversation_id": (
            conversation_id
        ),
        "feature": updated,
        "disabled_children": (
            disabled_children
        ),
    }