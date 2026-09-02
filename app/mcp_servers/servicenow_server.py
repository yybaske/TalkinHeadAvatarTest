import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer


load_dotenv()


# =========================================================
# ServiceNow
# =========================================================

SERVICENOW_INSTANCE_URL = (
    os.getenv(
        "SERVICENOW_INSTANCE_URL",
        "",
    )
    .strip()
    .rstrip("/")
)

SERVICENOW_USERNAME = (
    os.getenv(
        "SERVICENOW_USERNAME",
        "",
    )
    .strip()
)

SERVICENOW_PASSWORD = (
    os.getenv(
        "SERVICENOW_PASSWORD",
        "",
    )
)

SERVICENOW_VERIFY_SSL = (
    os.getenv(
        "SERVICENOW_VERIFY_SSL",
        "true",
    )
    .strip()
    .lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


# =========================================================
# MCP Server
# =========================================================

mcp = MCPServer(
    "ServiceNow"
)


# =========================================================
# Security
# =========================================================
#
# 最初から任意のServiceNowテーブルへ
# アクセスできるようにはしない。
#
# 必要なテーブルだけ追加する。
#

ALLOWED_TABLES = {
    "incident",
    "problem",
    "change_request",
    "cmdb_ci",
    "cmdb_ci_server",
}


DEFAULT_FIELDS = {
    "incident": [
        "sys_id",
        "number",
        "short_description",
        "description",
        "state",
        "priority",
        "assignment_group",
        "assigned_to",
        "sys_created_on",
        "sys_updated_on",
    ],
    "problem": [
        "sys_id",
        "number",
        "short_description",
        "description",
        "state",
        "priority",
        "assignment_group",
        "assigned_to",
        "sys_created_on",
        "sys_updated_on",
    ],
    "change_request": [
        "sys_id",
        "number",
        "short_description",
        "description",
        "state",
        "risk",
        "assignment_group",
        "assigned_to",
        "start_date",
        "end_date",
        "sys_created_on",
        "sys_updated_on",
    ],
    "cmdb_ci": [
        "sys_id",
        "name",
        "sys_class_name",
        "operational_status",
        "install_status",
        "manufacturer",
        "model_id",
        "serial_number",
        "sys_created_on",
        "sys_updated_on",
    ],
    "cmdb_ci_server": [
        "sys_id",
        "name",
        "sys_class_name",
        "operational_status",
        "install_status",
        "manufacturer",
        "model_id",
        "serial_number",
        "os",
        "os_version",
        "cpu_count",
        "ram",
        "sys_created_on",
        "sys_updated_on",
    ],
}


# =========================================================
# Validation
# =========================================================

def _validate_settings() -> None:
    if not SERVICENOW_INSTANCE_URL:
        raise RuntimeError(
            "SERVICENOW_INSTANCE_URL "
            "が設定されていません。"
        )

    if not SERVICENOW_USERNAME:
        raise RuntimeError(
            "SERVICENOW_USERNAME "
            "が設定されていません。"
        )

    if not SERVICENOW_PASSWORD:
        raise RuntimeError(
            "SERVICENOW_PASSWORD "
            "が設定されていません。"
        )


def _validate_table(
    table: str,
) -> str:
    normalized = (
        table
        .strip()
        .lower()
    )

    if normalized not in ALLOWED_TABLES:
        raise ValueError(
            f"テーブル '{normalized}' は"
            "MCPからの参照を許可していません。"
        )

    return normalized


# =========================================================
# ServiceNow API
# =========================================================

async def _get_records(
    table: str,
    sysparm_query: str = "",
    limit: int = 10,
) -> list[dict[str, Any]]:
    _validate_settings()

    table = _validate_table(
        table
    )

    limit = max(
        1,
        min(
            limit,
            100,
        ),
    )

    fields = DEFAULT_FIELDS.get(
        table,
        [
            "sys_id",
        ],
    )

    url = (
        f"{SERVICENOW_INSTANCE_URL}"
        f"/api/now/table/{table}"
    )

    params = {
        "sysparm_limit": str(
            limit
        ),
        "sysparm_display_value": (
            "true"
        ),
        "sysparm_exclude_reference_link": (
            "true"
        ),
        "sysparm_fields": ",".join(
            fields
        ),
    }

    if sysparm_query.strip():
        params[
            "sysparm_query"
        ] = sysparm_query.strip()

    async with httpx.AsyncClient(
        verify=SERVICENOW_VERIFY_SSL,
        timeout=30.0,
        auth=(
            SERVICENOW_USERNAME,
            SERVICENOW_PASSWORD,
        ),
    ) as client:

        response = await client.get(
            url,
            params=params,
            headers={
                "Accept": (
                    "application/json"
                ),
            },
        )

        response.raise_for_status()

        payload = response.json()

    result = payload.get(
        "result",
        [],
    )

    if not isinstance(
        result,
        list,
    ):
        return []

    return result


# =========================================================
# MCP Tools
# =========================================================

@mcp.tool()
async def search_servicenow_records(
    table: str,
    sysparm_query: str = "",
    limit: int = 10,
) -> dict:
    """
    ServiceNowのレコードを検索します。

    読み取り専用です。

    table:
        incident
        problem
        change_request
        cmdb_ci
        cmdb_ci_server

    sysparm_query:
        ServiceNow encoded query。

        例:
        active=true

        例:
        priority=1

        例:
        short_descriptionLIKEserver

    limit:
        最大取得件数。
        1～100。
    """

    records = await _get_records(
        table=table,
        sysparm_query=(
            sysparm_query
        ),
        limit=limit,
    )

    return {
        "table": table,
        "query": (
            sysparm_query
        ),
        "count": len(
            records
        ),
        "records": records,
    }


@mcp.tool()
async def get_servicenow_incidents(
    query: str = "",
    limit: int = 10,
) -> dict:
    """
    ServiceNowのインシデントを取得します。

    読み取り専用です。

    queryにはServiceNow encoded queryを
    指定できます。
    """

    records = await _get_records(
        table="incident",
        sysparm_query=query,
        limit=limit,
    )

    return {
        "table": "incident",
        "query": query,
        "count": len(
            records
        ),
        "records": records,
    }


# =========================================================
# Main
# =========================================================

if __name__ == "__main__":
    mcp.run(
        transport=(
            "streamable-http"
        ),
        host="127.0.0.1",
        port=8001,
        streamable_http_path=(
            "/mcp"
        ),
        stateless_http=True,
        json_response=True,
    )