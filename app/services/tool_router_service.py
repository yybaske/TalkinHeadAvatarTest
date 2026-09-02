from app.repositories.conversation_feature_repository import (
    initialize_conversation_features,
    is_conversation_feature_enabled,
)
from app.services.mcp_service import (
    get_mcp_servers,
    list_server_tools,
)


MCP_FEATURE_SERVER_ALIASES = {
    "mcp_local": {
        "localtools",
    },
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


MCP_FEATURE_DISPLAY_NAMES = {
    "mcp_local": "ローカルMCP",
    "mcp_servicenow": "ServiceNow",
    "mcp_aws": "AWS",
    "mcp_github": "GitHub",
    "mcp_sharepoint": "SharePoint",
}


def _normalize_name(
    value: str,
) -> str:
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
    return (
        is_conversation_feature_enabled(
            conversation_id=conversation_id,
            feature_key=feature_key,
        )
    )


async def get_tool_context(
    conversation_id: str,
) -> dict:
    initialize_conversation_features(
        conversation_id
    )

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

    llm_tools = []

    if local_rag_enabled:
        llm_tools.append(
            {
                "name": "local_document_search",
                "type": "local_rag",
                "provider": "local",
                "description": (
                    "登録済みの社内文書を検索します。"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "検索する質問またはキーワード"
                            ),
                        },
                    },
                    "required": [
                        "query"
                    ],
                },
                "read_only": True,
                "requires_confirmation": False,
                "executable": True,
            }
        )

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

            if not feature_enabled:
                continue

            enabled_capabilities.append(
                feature_key
            )

            server = (
                _find_server_for_feature(
                    feature_key=feature_key,
                    servers=mcp_servers,
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
                            "対応するMCPサーバー設定がありません。"
                        ),
                    }
                )

                continue

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
                        "connected": False,
                        "tool_count": 0,
                        "error": str(
                            e
                        ),
                    }
                )

                continue

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

            for tool in server_tools:
                tool_name = (
                    tool.get(
                        "name"
                    )
                )

                if not tool_name:
                    continue

                llm_tools.append(
                    {
                        "name": (
                            tool_name
                        ),
                        "type": "mcp",
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
                                "type": "object",
                                "properties": {},
                            }
                        ),
                        "server_name": (
                            server[
                                "name"
                            ]
                        ),
                        "read_only": None,
                        "requires_confirmation": True,
                        "executable": True,
                        "external_actions_enabled": (
                            external_actions_enabled
                        ),
                    }
                )

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