from app.repositories.conversation_feature_repository import (
    initialize_conversation_features,
    is_conversation_feature_enabled,
)
from app.services.mcp_service import (
    get_mcp_servers,
    list_server_tools,
)


# =========================================================
# Feature と MCP Server の対応
# =========================================================
#
# MCP_SERVERS の name が、
#
# ServiceNow
# AWS
# GitHub
# SharePoint
#
# のようになっていても判定できるようにする。
#

MCP_FEATURE_SERVER_ALIASES = {
    "mcp_servicenow": {
        "servicenow",
        "service_now",
        "service-now",
    },
    "mcp_aws": {
        "aws",
        "amazon_web_services",
        "amazon-web-services",
    },
    "mcp_github": {
        "github",
        "git_hub",
        "git-hub",
    },
    "mcp_sharepoint": {
        "sharepoint",
        "share_point",
        "share-point",
    },
}


# 表示名
MCP_FEATURE_DISPLAY_NAMES = {
    "mcp_servicenow": "ServiceNow",
    "mcp_aws": "AWS",
    "mcp_github": "GitHub",
    "mcp_sharepoint": "SharePoint",
}


def _normalize_name(
    value: str,
) -> str:
    """
    MCPサーバー名比較用の正規化。
    """

    return (
        value
        .strip()
        .lower()
        .replace(" ", "_")
    )


def _find_server_for_feature(
    feature_key: str,
    servers: list[dict],
) -> dict | None:
    """
    Featureに対応するMCPサーバーを取得する。
    """

    aliases = (
        MCP_FEATURE_SERVER_ALIASES
        .get(
            feature_key,
            set(),
        )
    )

    normalized_aliases = {
        _normalize_name(
            alias
        )
        for alias in aliases
    }

    for server in servers:

        server_name = (
            server
            .get(
                "name",
                "",
            )
        )

        normalized_server_name = (
            _normalize_name(
                server_name
            )
        )

        if (
            normalized_server_name
            in normalized_aliases
        ):
            return server

    return None


def _is_enabled(
    conversation_id: str,
    feature_key: str,
) -> bool:
    """
    管理者設定
    AND
    会話設定

    の実効Feature状態を返す。
    """

    return (
        is_conversation_feature_enabled(
            conversation_id=(
                conversation_id
            ),
            feature_key=(
                feature_key
            ),
        )
    )


async def get_tool_context(
    conversation_id: str,
) -> dict:
    """
    この会話で利用可能なToolを判定する。

    判定対象:

    - Local RAG
    - MCP
    - ServiceNow
    - AWS
    - GitHub
    - SharePoint
    - External Actions

    MCPについては実際にMCPサーバーから
    Tool一覧を取得する。
    """

    # ---------------------------------------------------------
    # 会話Feature初期化
    # ---------------------------------------------------------

    initialize_conversation_features(
        conversation_id
    )

    # ---------------------------------------------------------
    # Feature状態
    # ---------------------------------------------------------

    local_rag_enabled = (
        _is_enabled(
            conversation_id,
            "local_rag",
        )
    )

    mcp_enabled = (
        _is_enabled(
            conversation_id,
            "mcp",
        )
    )

    external_actions_enabled = (
        _is_enabled(
            conversation_id,
            "external_actions",
        )
    )

    # ---------------------------------------------------------
    # Capability
    # ---------------------------------------------------------

    enabled_capabilities = []

    if local_rag_enabled:
        enabled_capabilities.append(
            "local_rag"
        )

    if mcp_enabled:
        enabled_capabilities.append(
            "mcp"
        )

    if external_actions_enabled:
        enabled_capabilities.append(
            "external_actions"
        )

    # ---------------------------------------------------------
    # LLMへ渡してよいTool
    # ---------------------------------------------------------

    llm_tools = []

    # Local RAG
    if local_rag_enabled:

        llm_tools.append(
            {
                "name": (
                    "local_document_search"
                ),
                "type": (
                    "local_rag"
                ),
                "provider": (
                    "local"
                ),
                "description": (
                    "登録済みの社内文書を"
                    "検索します。"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "検索する質問または"
                                "キーワード"
                            ),
                        },
                    },
                    "required": [
                        "query"
                    ],
                },
                "read_only": True,
                "requires_confirmation": (
                    False
                ),
                "executable": True,
            }
        )

    # ---------------------------------------------------------
    # MCP
    # ---------------------------------------------------------

    mcp_servers = []
    mcp_results = []
    pending_connectors = []

    if mcp_enabled:

        mcp_servers = (
            get_mcp_servers()
        )

        for feature_key in (
            MCP_FEATURE_SERVER_ALIASES
        ):

            feature_enabled = (
                _is_enabled(
                    conversation_id,
                    feature_key,
                )
            )

            display_name = (
                MCP_FEATURE_DISPLAY_NAMES
                .get(
                    feature_key,
                    feature_key,
                )
            )

            # ---------------------------------------------
            # 会話でOFF
            # ---------------------------------------------

            if not feature_enabled:
                continue

            enabled_capabilities.append(
                feature_key
            )

            # ---------------------------------------------
            # 対応MCPサーバーを探す
            # ---------------------------------------------

            server = (
                _find_server_for_feature(
                    feature_key=(
                        feature_key
                    ),
                    servers=(
                        mcp_servers
                    ),
                )
            )

            if server is None:

                pending_connectors.append(
                    {
                        "feature_key": (
                            feature_key
                        ),
                        "display_name": (
                            display_name
                        ),
                        "reason": (
                            "対応するMCPサーバー"
                            "設定がありません。"
                        ),
                    }
                )

                continue

            # ---------------------------------------------
            # MCP Tool一覧取得
            # ---------------------------------------------

            try:
                server_tools = (
                    await list_server_tools(
                        server
                    )
                )

            except Exception as e:

                mcp_results.append(
                    {
                        "feature_key": (
                            feature_key
                        ),
                        "display_name": (
                            display_name
                        ),
                        "server_name": (
                            server[
                                "name"
                            ]
                        ),
                        "connected": (
                            False
                        ),
                        "tool_count": 0,
                        "error": str(
                            e
                        ),
                    }
                )

                continue

            # list_server_tools は現在、
            # 接続エラー時に [] を返す設計なので、
            # Tool 0件の場合も保持する。

            mcp_results.append(
                {
                    "feature_key": (
                        feature_key
                    ),
                    "display_name": (
                        display_name
                    ),
                    "server_name": (
                        server[
                            "name"
                        ]
                    ),
                    "connected": True,
                    "tool_count": len(
                        server_tools
                    ),
                    "error": None,
                }
            )

            # ---------------------------------------------
            # MCP ToolをLLM公開候補へ
            # ---------------------------------------------

            for tool in server_tools:

                tool_name = (
                    tool.get(
                        "name"
                    )
                )

                if not tool_name:
                    continue

                #
                # 現段階ではMCP Toolが
                # 読取系か更新系かを
                # 確実に判定できない。
                #
                # そのため、MCP Toolは
                # 原則 confirmation 必須として扱う。
                #
                # 次の段階でMCP annotations等を使って
                # read_only判定を追加する。
                #

                llm_tools.append(
                    {
                        "name": (
                            tool_name
                        ),
                        "type": (
                            "mcp"
                        ),
                        "provider": (
                            feature_key
                        ),
                        "display_name": (
                            tool.get(
                                "title"
                            )
                            or tool_name
                        ),
                        "description": (
                            tool.get(
                                "description"
                            )
                            or ""
                        ),
                        "input_schema": (
                            tool.get(
                                "input_schema"
                            )
                            or {
                                "type": (
                                    "object"
                                ),
                                "properties": {},
                            }
                        ),
                        "server_name": (
                            server[
                                "name"
                            ]
                        ),

                        # MCP Toolはまだ
                        # read/write分類前
                        "read_only": None,

                        # 安全側に倒して
                        # 現時点では確認必須
                        "requires_confirmation": (
                            True
                        ),

                        "executable": True,

                        # 外部更新が許可されているか
                        "external_actions_enabled": (
                            external_actions_enabled
                        ),
                    }
                )

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    return {
        "status": "ok",

        "conversation_id": (
            conversation_id
        ),

        "effective_features": {
            "local_rag": (
                local_rag_enabled
            ),
            "mcp": (
                mcp_enabled
            ),
            "external_actions": (
                external_actions_enabled
            ),
        },

        "enabled_capabilities": (
            enabled_capabilities
        ),

        "llm_tool_count": len(
            llm_tools
        ),

        "llm_tools": (
            llm_tools
        ),

        "mcp": {
            "enabled": (
                mcp_enabled
            ),
            "configured_server_count": (
                len(
                    mcp_servers
                )
            ),
            "servers": (
                mcp_results
            ),
        },

        "pending_connectors": (
            pending_connectors
        ),
    }