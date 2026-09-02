from mcp.server import MCPServer


mcp = MCPServer(
    "LocalTools"
)


@mcp.tool()
def add_numbers(
    a: int,
    b: int,
) -> int:
    """
    2つの整数を足し算します。
    """

    return a + b


@mcp.tool()
def echo_text(
    text: str,
) -> str:
    """
    受け取った文字列をそのまま返します。
    """

    return text


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )