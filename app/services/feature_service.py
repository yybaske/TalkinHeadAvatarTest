from app.repositories.feature_repository import (
    get_feature,
    is_feature_enabled,
    list_features,
    update_feature,
)


MCP_CHILD_FEATURES = {
    "mcp_servicenow",
    "mcp_aws",
    "mcp_github",
    "mcp_sharepoint",
}


def get_features() -> dict:
    features = list_features()

    categories = {}

    for feature in features:
        category = feature[
            "category"
        ]

        if category not in categories:
            categories[
                category
            ] = []

        categories[
            category
        ].append(
            feature
        )

    return {
        "status": "ok",
        "count": len(
            features
        ),
        "features": features,
        "categories": categories,
    }


def get_feature_status(
    feature_key: str,
) -> dict:
    feature = get_feature(
        feature_key
    )

    if feature is None:
        raise ValueError(
            "指定された機能は存在しません。"
        )

    return {
        "status": "ok",
        "feature": feature,
    }


def set_feature_status(
    feature_key: str,
    enabled: bool,
) -> dict:
    feature = get_feature(
        feature_key
    )

    if feature is None:
        raise ValueError(
            "指定された機能は存在しません。"
        )

    if (
        enabled
        and feature_key
        in MCP_CHILD_FEATURES
    ):
        if not is_feature_enabled(
            "mcp"
        ):
            raise ValueError(
                "MCP連携が無効です。"
                "先にMCP連携を有効にしてください。"
            )

    updated = update_feature(
        feature_key=feature_key,
        enabled=enabled,
    )

    if updated is None:
        raise ValueError(
            "機能設定の更新に失敗しました。"
        )

    disabled_children = []

    if (
        feature_key == "mcp"
        and enabled is False
    ):
        for child_key in (
            MCP_CHILD_FEATURES
        ):
            if is_feature_enabled(
                child_key
            ):
                update_feature(
                    feature_key=child_key,
                    enabled=False,
                )

                disabled_children.append(
                    child_key
                )

    return {
        "status": "ok",
        "feature": updated,
        "disabled_children": (
            disabled_children
        ),
    }