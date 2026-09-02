import json
import os

from dotenv import load_dotenv


load_dotenv()


def _load_mcp_servers() -> list[dict]:
    raw_value = os.getenv(
        "MCP_SERVERS",
        "[]",
    ).strip()

    if not raw_value:
        return []

    try:
        value = json.loads(
            raw_value
        )
    except json.JSONDecodeError as e:
        raise RuntimeError(
            "MCP_SERVERS のJSON形式が正しくありません。"
        ) from e

    if not isinstance(
        value,
        list,
    ):
        raise RuntimeError(
            "MCP_SERVERS はJSON配列で指定してください。"
        )

    return [
        server
        for server in value
        if isinstance(
            server,
            dict,
        )
    ]


def _get_bool_env(
    name: str,
    default: bool = False,
) -> bool:
    raw_value = os.getenv(
        name,
        str(default),
    )

    return (
        raw_value
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


class Settings:
    APP_ENV = os.getenv(
        "APP_ENV",
        "local",
    )

    DB_HOST = os.getenv(
        "DB_HOST",
        "127.0.0.1",
    )

    DB_PORT = int(
        os.getenv(
            "DB_PORT",
            "5432",
        )
    )

    DB_NAME = os.getenv(
        "DB_NAME",
        "ragdb",
    )

    DB_USER = os.getenv(
        "DB_USER",
        "raguser",
    )

    DB_PASSWORD = os.getenv(
        "DB_PASSWORD",
        "",
    )

    OPENAI_API_KEY = os.getenv(
        "OPENAI_API_KEY",
        "",
    )

    EMBEDDING_MODEL = (
        "text-embedding-3-small"
    )

    RAG_MODEL = (
        "gpt-5.6-luna"
    )

    EMBEDDING_DIMENSIONS = 1536

    MCP_ENABLED = _get_bool_env(
        "MCP_ENABLED",
        False,
    )

    MCP_SERVERS = (
        _load_mcp_servers()
    )

    AUTH_SECRET_KEY = os.getenv(
        "AUTH_SECRET_KEY",
        "",
    )

    AUTH_COOKIE_NAME = os.getenv(
        "AUTH_COOKIE_NAME",
        "rag_session",
    )

    AUTH_EXPIRE_MINUTES = int(
        os.getenv(
            "AUTH_EXPIRE_MINUTES",
            "480",
        )
    )

    AUTH_COOKIE_SECURE = (
        _get_bool_env(
            "AUTH_COOKIE_SECURE",
            False,
        )
    )


settings = Settings()


if not settings.OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY が設定されていません。"
    )


if not settings.AUTH_SECRET_KEY:
    raise RuntimeError(
        "AUTH_SECRET_KEY が設定されていません。"
    )