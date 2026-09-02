from typing import Any

from mcp import Client

from app.core.config import settings


def get_mcp_servers() -> list[dict]:
    """
    設定済みMCPサーバー一覧を返す。
    """

    if not settings.MCP_ENABLED:
        return []

    result = []

    for server in settings.MCP_SERVERS:
        name = (
            server
            .get(
                "name",
                "",
            )
            .strip()
        )

        url = (
            server
            .get(
                "url",
                "",
            )
            .strip()
        )

        if not name:
            continue

        if not url:
            continue

        result.append(
            {
                "name": name,
                "url": url,
                "enabled": server.get(
                    "enabled",
                    True,
                ),
            }
        )

    return [
        server
        for server in result
        if server["enabled"]
    ]


async def get_mcp_status() -> dict:
    """
    MCP全体の状態を取得する。
    """

    if not settings.MCP_ENABLED:
        return {
            "enabled": False,
            "server_count": 0,
            "servers": [],
        }

    servers = get_mcp_servers()

    server_results = []

    for server in servers:
        result = await check_server(
            server
        )

        server_results.append(
            result
        )

    return {
        "enabled": True,
        "server_count": len(
            server_results
        ),
        "servers": server_results,
    }


async def check_server(
    server: dict,
) -> dict:
    """
    MCPサーバーへの接続確認。
    """

    try:
        async with Client(
            server["url"]
        ) as client:

            server_info = (
                client.server_info
            )

            return {
                "name": server["name"],
                "url": server["url"],
                "connected": True,
                "server_name": (
                    getattr(
                        server_info,
                        "name",
                        None,
                    )
                    if server_info
                    else None
                ),
                "server_version": (
                    getattr(
                        server_info,
                        "version",
                        None,
                    )
                    if server_info
                    else None
                ),
                "protocol_version": (
                    client.protocol_version
                ),
                "error": None,
            }

    except Exception as e:
        return {
            "name": server["name"],
            "url": server["url"],
            "connected": False,
            "server_name": None,
            "server_version": None,
            "protocol_version": None,
            "error": str(e),
        }


async def list_all_mcp_tools() -> dict:
    """
    全MCPサーバーから利用可能なToolを取得する。
    """

    if not settings.MCP_ENABLED:
        return {
            "enabled": False,
            "count": 0,
            "tools": [],
        }

    servers = get_mcp_servers()

    tools = []

    for server in servers:

        server_tools = (
            await list_server_tools(
                server
            )
        )

        tools.extend(
            server_tools
        )

    return {
        "enabled": True,
        "count": len(tools),
        "tools": tools,
    }


async def list_server_tools(
    server: dict,
) -> list[dict]:
    """
    指定MCPサーバーのTool一覧を取得する。
    """

    try:
        async with Client(
            server["url"]
        ) as client:

            response = (
                await client.list_tools()
            )

            result = []

            for tool in response.tools:

                result.append(
                    {
                        "server_name": (
                            server["name"]
                        ),
                        "name": tool.name,
                        "title": getattr(
                            tool,
                            "title",
                            None,
                        ),
                        "description": (
                            tool.description
                        ),
                        "input_schema": (
                            tool.input_schema
                        ),
                    }
                )

            return result

    except Exception:
        return []


async def call_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict:
    """
    MCP Toolを実行する。

    現時点ではAPIとして直接公開しない。
    将来Tool Routerからのみ呼び出す。
    """

    server = _find_server(
        server_name
    )

    if not server:
        raise ValueError(
            "指定されたMCPサーバーが"
            "存在しません。"
        )

    async with Client(
        server["url"]
    ) as client:

        response = await client.call_tool(
            tool_name,
            arguments,
        )

        content = []

        for item in response.content:

            text = getattr(
                item,
                "text",
                None,
            )

            if text is not None:
                content.append(
                    text
                )

        return {
            "server_name": server_name,
            "tool_name": tool_name,
            "is_error": response.is_error,
            "content": content,
            "structured_content": (
                response.structured_content
            ),
        }


def _find_server(
    server_name: str,
) -> dict | None:

    for server in get_mcp_servers():

        if (
            server["name"]
            == server_name
        ):
            return server

    return None