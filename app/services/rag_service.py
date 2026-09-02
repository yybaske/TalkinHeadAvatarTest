import asyncio
import json
import re
from typing import Any

from app.core.config import settings
from app.core.openai_client import client
from app.repositories.conversation_feature_repository import (
    is_conversation_feature_enabled,
)
from app.repositories.document_repository import (
    hybrid_search,
)
from app.repositories.feature_repository import (
    is_feature_enabled,
)
from app.services.embedding_service import (
    create_embedding,
)
from app.services.mcp_service import (
    call_mcp_tool,
)
from app.services.tool_router_service import (
    get_tool_context,
)


MIN_LEXICAL_SCORE = 0.20
MAX_VECTOR_DISTANCE_HIGH = 0.45
MAX_VECTOR_DISTANCE_MEDIUM = 0.58


# =========================================================
# MCP
# =========================================================

#
# 現時点で確認なしに実行してよい
# ローカルMCP Tool。
#
# ServiceNow等を追加した場合は
# ここには追加せず、
# 将来的に確認画面を経由させる。
#
SAFE_LOCAL_MCP_TOOLS = {
    "add_numbers",
    "echo_text",
}


# =========================================================
# Search
# =========================================================

def search(
    query: str,
    history: list[dict] | None = None,
    limit: int = 5,
) -> dict:
    original_query = query.strip()

    if not original_query:
        raise ValueError(
            "検索文字列を入力してください。"
        )

    search_query = rewrite_query(
        original_query,
        history,
    )

    query_embedding = create_embedding(
        search_query
    )

    candidates = hybrid_search(
        query=search_query,
        embedding=query_embedding,
        limit=20,
        candidate_limit=30,
    )

    results = rerank_chunks(
        query=search_query,
        candidates=candidates,
        limit=limit,
    )

    answerability = (
        evaluate_answerability(
            results
        )
    )

    return {
        "status": "ok",
        "search_type": (
            "hybrid_rerank"
        ),
        "original_query": (
            original_query
        ),
        "search_query": (
            search_query
        ),
        "candidate_count": len(
            candidates
        ),
        "count": len(
            results
        ),
        "answerable": (
            answerability[
                "answerable"
            ]
        ),
        "confidence": (
            answerability[
                "confidence"
            ]
        ),
        "results": results,
    }


# =========================================================
# Chat
# =========================================================

def chat(
    query: str,
    history: list[dict] | None = None,
    conversation_id: str | None = None,
) -> dict:
    original_query = (
        query.strip()
    )

    if not original_query:
        raise ValueError(
            "質問を入力してください。"
        )

    normalized_history = (
        _normalize_history(
            history
        )
    )

    # =====================================================
    # 1. Feature判定
    # =====================================================

    local_rag_enabled = (
        _is_chat_feature_enabled(
            conversation_id=(
                conversation_id
            ),
            feature_key=(
                "local_rag"
            ),
        )
    )

    mcp_enabled = (
        _is_chat_feature_enabled(
            conversation_id=(
                conversation_id
            ),
            feature_key="mcp",
        )
    )

    # =====================================================
    # 2. MCP Tool Calling
    # =====================================================

    #
    # MCPがONで、
    # conversation_idが存在する場合だけ
    # Tool Routerを見る。
    #
    if (
        mcp_enabled
        and conversation_id
    ):
        mcp_result = (
            _try_mcp_tool_call(
                query=original_query,
                history=(
                    normalized_history
                ),
                conversation_id=(
                    conversation_id
                ),
            )
        )

        if mcp_result is not None:
            return mcp_result

    # =====================================================
    # 3. Local RAG OFF
    # =====================================================

    if not local_rag_enabled:
        answer = (
            generate_conversation_answer(
                query=original_query,
                history=(
                    normalized_history
                ),
            )
        )

        return {
            "status": "ok",
            "mode": "conversation",
            "retrieval_used": False,
            "answerable": True,
            "confidence": (
                "feature_disabled"
            ),
            "original_query": (
                original_query
            ),
            "search_query": None,
            "answer": answer,
            "sources": [],
            "features": {
                "local_rag": False,
                "mcp": (
                    mcp_enabled
                ),
            },
            "tool_calls": [],
        }

    # =====================================================
    # 4. Retrieval Gate
    # =====================================================

    retrieval_required = (
        should_retrieve(
            query=original_query,
            history=(
                normalized_history
            ),
        )
    )

    # =====================================================
    # 5. RAG不要
    # =====================================================

    if not retrieval_required:
        answer = (
            generate_conversation_answer(
                query=original_query,
                history=(
                    normalized_history
                ),
            )
        )

        return {
            "status": "ok",
            "mode": "conversation",
            "retrieval_used": False,
            "answerable": True,
            "confidence": (
                "conversation"
            ),
            "original_query": (
                original_query
            ),
            "search_query": None,
            "answer": answer,
            "sources": [],
            "features": {
                "local_rag": True,
                "mcp": (
                    mcp_enabled
                ),
            },
            "tool_calls": [],
        }

    # =====================================================
    # 6. Query Rewrite
    # =====================================================

    search_query = rewrite_query(
        original_query,
        normalized_history,
    )

    # =====================================================
    # 7. Embedding
    # =====================================================

    query_embedding = (
        create_embedding(
            search_query
        )
    )

    # =====================================================
    # 8. Hybrid Search
    # =====================================================

    candidates = hybrid_search(
        query=search_query,
        embedding=query_embedding,
        limit=20,
        candidate_limit=30,
    )

    # =====================================================
    # 9. Rerank
    # =====================================================

    chunks = rerank_chunks(
        query=search_query,
        candidates=candidates,
        limit=5,
    )

    # =====================================================
    # 10. Answerability Gate
    # =====================================================

    answerability = (
        evaluate_answerability(
            chunks
        )
    )

    if not answerability[
        "answerable"
    ]:
        return {
            "status": "ok",
            "mode": "rag",
            "retrieval_used": True,
            "answerable": False,
            "confidence": (
                answerability[
                    "confidence"
                ]
            ),
            "original_query": (
                original_query
            ),
            "search_query": (
                search_query
            ),
            "answer": (
                "登録済み文書から、"
                "質問に回答できる十分な"
                "根拠を見つけられませんでした。"
            ),
            "sources": [],
            "features": {
                "local_rag": True,
                "mcp": (
                    mcp_enabled
                ),
            },
            "tool_calls": [],
        }

    # =====================================================
    # 11. Answer Generation
    # =====================================================

    answer = generate_answer(
        query=original_query,
        chunks=chunks,
        history=normalized_history,
    )

    sources = [
        _build_source_response(
            index=index,
            chunk=chunk,
        )
        for index, chunk
        in enumerate(
            chunks,
            start=1,
        )
    ]

    return {
        "status": "ok",
        "mode": "rag",
        "retrieval_used": True,
        "answerable": True,
        "confidence": (
            answerability[
                "confidence"
            ]
        ),
        "original_query": (
            original_query
        ),
        "search_query": (
            search_query
        ),
        "answer": answer,
        "sources": sources,
        "features": {
            "local_rag": True,
            "mcp": (
                mcp_enabled
            ),
        },
        "tool_calls": [],
    }


# =========================================================
# MCP Tool Calling
# =========================================================

def _try_mcp_tool_call(
    query: str,
    history: list[dict],
    conversation_id: str,
) -> dict | None:
    """
    MCP Toolが利用可能なら、
    LLMにTool選択をさせる。

    Tool不要と判断された場合は
    Noneを返し、通常RAGへ進む。
    """

    tool_context = _run_async(
        get_tool_context(
            conversation_id
        )
    )

    llm_tools = (
        tool_context.get(
            "llm_tools",
            [],
        )
    )

    #
    # Local RAGはここでは
    # Tool Calling対象にしない。
    #
    # 従来のRAGパイプラインで
    # 処理する。
    #
    mcp_tools = [
        tool
        for tool in llm_tools
        if tool.get(
            "type"
        ) == "mcp"
        and tool.get(
            "executable"
        )
    ]

    if not mcp_tools:
        return None

    openai_tools = (
        _build_openai_tools(
            mcp_tools
        )
    )

    if not openai_tools:
        return None

    conversation = (
        _normalize_history(
            history
        )
    )

    # =====================================================
    # LLMにTool選択させる
    # =====================================================

    response = (
        client.responses.create(
            model=settings.RAG_MODEL,
            instructions=(
                "You are a tool router. "
                "Answer in Japanese. "
                "You have access to MCP tools. "
                "Use a tool only when the user's "
                "request clearly requires one of "
                "the available tools. "
                "If no tool is necessary, do not "
                "call any tool. "
                "Do not call local_document_search. "
                "For arithmetic, use the available "
                "calculation tool when appropriate."
            ),
            input=[
                *conversation,
                {
                    "role": "user",
                    "content": query,
                },
            ],
            tools=openai_tools,
            tool_choice="auto",
        )
    )

    tool_call = (
        _get_first_function_call(
            response
        )
    )

    #
    # LLMがToolを選ばなかった
    # → 従来RAGへ
    #
    if tool_call is None:
        return None

    tool_name = (
        tool_call[
            "name"
        ]
    )

    selected_tool = (
        _find_mcp_tool(
            tools=mcp_tools,
            tool_name=tool_name,
        )
    )

    if selected_tool is None:
        return None

    # =====================================================
    # Arguments
    # =====================================================

    try:
        arguments = json.loads(
            tool_call[
                "arguments"
            ]
            or "{}"
        )

    except json.JSONDecodeError:
        arguments = {}

    if not isinstance(
        arguments,
        dict,
    ):
        arguments = {}

    # =====================================================
    # Confirmation Gate
    # =====================================================

    if _tool_requires_confirmation(
        selected_tool
    ):
        return {
            "status": "ok",
            "mode": "tool_confirmation",
            "retrieval_used": False,
            "answerable": True,
            "confidence": (
                "confirmation_required"
            ),
            "original_query": query,
            "search_query": None,
            "answer": (
                f"MCPツール「{tool_name}」の"
                "実行には確認が必要です。"
            ),
            "sources": [],
            "features": {
                "local_rag": (
                    _is_chat_feature_enabled(
                        conversation_id,
                        "local_rag",
                    )
                ),
                "mcp": True,
            },
            "tool_calls": [
                {
                    "tool_name": (
                        tool_name
                    ),
                    "server_name": (
                        selected_tool.get(
                            "server_name"
                        )
                    ),
                    "arguments": (
                        arguments
                    ),
                    "executed": False,
                    "confirmation_required": (
                        True
                    ),
                }
            ],
        }

    # =====================================================
    # MCP実行
    # =====================================================

    server_name = (
        selected_tool.get(
            "server_name"
        )
    )

    if not server_name:
        raise RuntimeError(
            "MCP Toolのserver_nameが"
            "取得できません。"
        )

    tool_result = _run_async(
        call_mcp_tool(
            server_name=(
                server_name
            ),
            tool_name=(
                tool_name
            ),
            arguments=(
                arguments
            ),
        )
    )

    # =====================================================
    # Tool結果をLLMへ返す
    # =====================================================

    final_response = (
        client.responses.create(
            model=settings.RAG_MODEL,
            previous_response_id=(
                response.id
            ),
            input=[
                {
                    "type": (
                        "function_call_output"
                    ),
                    "call_id": (
                        tool_call[
                            "call_id"
                        ]
                    ),
                    "output": (
                        json.dumps(
                            tool_result,
                            ensure_ascii=False,
                            default=str,
                        )
                    ),
                }
            ],
            instructions=(
                "Answer the user's original "
                "question in Japanese using the "
                "tool result. "
                "Be concise and do not invent "
                "information that is not in the "
                "tool result."
            ),
        )
    )

    answer = (
        final_response
        .output_text
        .strip()
    )

    if not answer:
        answer = (
            "MCP Toolは実行されましたが、"
            "回答を生成できませんでした。"
        )

    return {
        "status": "ok",
        "mode": "mcp",
        "retrieval_used": False,
        "answerable": True,
        "confidence": "tool",
        "original_query": query,
        "search_query": None,
        "answer": answer,
        "sources": [],
        "features": {
            "local_rag": (
                _is_chat_feature_enabled(
                    conversation_id,
                    "local_rag",
                )
            ),
            "mcp": True,
        },
        "tool_calls": [
            {
                "tool_name": (
                    tool_name
                ),
                "server_name": (
                    server_name
                ),
                "arguments": (
                    arguments
                ),
                "executed": True,
                "confirmation_required": (
                    False
                ),
                "is_error": (
                    tool_result.get(
                        "is_error",
                        False,
                    )
                ),
            }
        ],
    }


def _build_openai_tools(
    tools: list[dict],
) -> list[dict]:
    """
    Tool Router形式から
    OpenAI Responses API形式へ変換する。
    """

    result = []

    for tool in tools:
        name = (
            tool.get(
                "name",
                "",
            )
            .strip()
        )

        if not name:
            continue

        description = (
            tool.get(
                "description",
                "",
            )
            .strip()
        )

        input_schema = (
            tool.get(
                "input_schema"
            )
            or {
                "type": "object",
                "properties": {},
            }
        )

        result.append(
            {
                "type": "function",
                "name": name,
                "description": (
                    description
                ),
                "parameters": (
                    input_schema
                ),
                "strict": False,
            }
        )

    return result


def _get_first_function_call(
    response: Any,
) -> dict | None:
    """
    Responses APIの出力から
    最初のfunction_callを取得する。
    """

    output = getattr(
        response,
        "output",
        None,
    )

    if not output:
        return None

    for item in output:
        item_type = getattr(
            item,
            "type",
            None,
        )

        if (
            item_type
            != "function_call"
        ):
            continue

        name = getattr(
            item,
            "name",
            None,
        )

        call_id = getattr(
            item,
            "call_id",
            None,
        )

        arguments = getattr(
            item,
            "arguments",
            "{}",
        )

        if not name:
            continue

        if not call_id:
            continue

        return {
            "name": name,
            "call_id": (
                call_id
            ),
            "arguments": (
                arguments
            ),
        }

    return None


def _find_mcp_tool(
    tools: list[dict],
    tool_name: str,
) -> dict | None:
    for tool in tools:
        if (
            tool.get(
                "name"
            )
            == tool_name
        ):
            return tool

    return None


def _tool_requires_confirmation(
    tool: dict,
) -> bool:
    """
    現段階ではLocalToolsの
    add_numbers / echo_textだけ
    自動実行可能。

    それ以外は安全側で確認必須。
    """

    provider = tool.get(
        "provider"
    )

    tool_name = tool.get(
        "name"
    )

    if (
        provider == "mcp_local"
        and tool_name
        in SAFE_LOCAL_MCP_TOOLS
    ):
        return False

    return bool(
        tool.get(
            "requires_confirmation",
            True,
        )
    )


def _run_async(
    awaitable,
):
    """
    現在のchat()が同期関数なので、
    async MCP処理を同期側から実行する。

    FastAPIの同期endpointは
    worker thread上で実行されるため、
    現在の構成ではasyncio.run()でよい。
    """

    try:
        asyncio.get_running_loop()

    except RuntimeError:
        return asyncio.run(
            awaitable
        )

    raise RuntimeError(
        "同期chat()からMCP処理を"
        "実行できませんでした。"
        "async endpointへの変更が必要です。"
    )


# =========================================================
# Feature
# =========================================================

def _is_chat_feature_enabled(
    conversation_id: str | None,
    feature_key: str,
) -> bool:
    """
    conversation_idがあれば
    管理者設定 AND 会話設定。

    conversation_idがない場合は
    管理者設定だけを見る。
    """

    if conversation_id:
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

    return is_feature_enabled(
        feature_key
    )


# =========================================================
# Answerability
# =========================================================

def evaluate_answerability(
    chunks: list[dict],
) -> dict:
    """
    検索結果が質問への回答根拠として
    十分かどうかを判定する。

    RRFは検索順位統合用のため、
    Answerability判定には使用しない。
    """

    if not chunks:
        return {
            "answerable": False,
            "confidence": "low",
        }

    top_chunks = chunks[:3]

    vector_distances = [
        chunk["distance"]
        for chunk in top_chunks
        if chunk.get(
            "distance"
        )
        is not None
    ]

    lexical_scores = [
        chunk[
            "lexical_score"
        ]
        for chunk in top_chunks
        if chunk.get(
            "lexical_score"
        )
        is not None
    ]

    best_distance = (
        min(
            vector_distances
        )
        if vector_distances
        else None
    )

    best_lexical = (
        max(
            lexical_scores
        )
        if lexical_scores
        else None
    )

    # =====================================================
    # HIGH
    # =====================================================

    if (
        best_distance is not None
        and best_distance
        <= MAX_VECTOR_DISTANCE_HIGH
    ):
        return {
            "answerable": True,
            "confidence": "high",
        }

    # =====================================================
    # HIGH
    # Semantic + Keyword
    # =====================================================

    if (
        best_distance is not None
        and best_distance
        <= MAX_VECTOR_DISTANCE_MEDIUM
        and best_lexical is not None
        and best_lexical
        >= MIN_LEXICAL_SCORE
    ):
        return {
            "answerable": True,
            "confidence": "high",
        }

    # =====================================================
    # MEDIUM
    # =====================================================

    if (
        best_lexical is not None
        and best_lexical >= 0.35
    ):
        return {
            "answerable": True,
            "confidence": "medium",
        }

    return {
        "answerable": False,
        "confidence": "low",
        "best_vector_distance": (
            best_distance
        ),
        "best_lexical_score": (
            best_lexical
        ),
    }


# =========================================================
# Retrieval Gate
# =========================================================

def should_retrieve(
    query: str,
    history: list[dict] | None,
) -> bool:
    text = query.strip()

    if not text:
        return False

    normalized = (
        text
        .lower()
        .strip()
    )

    greeting_patterns = [
        r"^こんにちは[！!。.]?$",
        r"^こんばんは[！!。.]?$",
        r"^おはよう(?:ございます)?[！!。.]?$",
        r"^はじめまして[！!。.]?$",
        r"^hello[！!。.]?$",
        r"^hi[！!。.]?$",
        r"^hey[！!。.]?$",
    ]

    if _matches_any(
        normalized,
        greeting_patterns,
    ):
        return False

    thanks_patterns = [
        r"^ありがとう(?:ございます)?[！!。.]?$",
        r"^ありがと[！!。.]?$",
        r"^助かりました[！!。.]?$",
        r"^助かった[！!。.]?$",
        r"^thanks?[！!。.]?$",
        r"^thank you[！!。.]?$",
    ]

    if _matches_any(
        normalized,
        thanks_patterns,
    ):
        return False

    acknowledgement_patterns = [
        r"^了解(?:です)?[！!。.]?$",
        r"^承知しました[！!。.]?$",
        r"^わかりました[！!。.]?$",
        r"^分かりました[！!。.]?$",
        r"^ok[！!。.]?$",
        r"^okay[！!。.]?$",
    ]

    if _matches_any(
        normalized,
        acknowledgement_patterns,
    ):
        return False

    if history:
        followup_patterns = [
            r"もっと簡単に",
            r"簡単に説明",
            r"わかりやすく",
            r"分かりやすく",
            r"もう少し詳しく",
            r"詳しく説明",
            r"短くして",
            r"簡潔に",
            r"要約して",
            r"まとめて",
            r"箇条書き",
            r"表にして",
            r"言い換えて",
            r"英語にして",
            r"日本語にして",
            r"翻訳して",
            r"どういう意味",
            r"つまり",
        ]

        if _contains_any(
            normalized,
            followup_patterns,
        ):
            return False

    return True


# =========================================================
# Query Rewrite
# =========================================================

def rewrite_query(
    query: str,
    history: list[dict] | None,
) -> str:
    conversation = (
        _normalize_history(
            history
        )
    )

    conversation.append(
        {
            "role": "user",
            "content": query,
        }
    )

    response = (
        client.responses.create(
            model=settings.RAG_MODEL,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Rewrite the latest user "
                        "question into one concise "
                        "English search query for "
                        "document retrieval. "
                        "Use conversation history "
                        "to resolve references. "
                        "Preserve technical terms, "
                        "product names and acronyms. "
                        "Do not answer the question. "
                        "Return only the search query."
                    ),
                },
                *conversation,
            ],
        )
    )

    rewritten = (
        response
        .output_text
        .strip()
    )

    return rewritten or query


# =========================================================
# Rerank
# =========================================================

def rerank_chunks(
    query: str,
    candidates: list[dict],
    limit: int = 5,
) -> list[dict]:
    if not candidates:
        return []

    candidate_data = [
        {
            "chunk_id": (
                item[
                    "chunk_id"
                ]
            ),
            "filename": (
                item[
                    "filename"
                ]
            ),
            "page_number": (
                item.get(
                    "page_number"
                )
            ),
            "section_title": (
                item.get(
                    "section_title"
                )
            ),
            "content": (
                item[
                    "content"
                ][:1500]
            ),
        }
        for item in candidates
    ]

    response = (
        client.responses.create(
            model=settings.RAG_MODEL,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a reranker for "
                        "a RAG system. "
                        "Rank chunks by usefulness "
                        "for answering the question. "
                        "Return JSON only: "
                        '{"chunk_ids":[1,2,3]}. '
                        "Do not return more IDs "
                        "than requested."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {query}\n"
                        f"Return the best "
                        f"{limit} chunks.\n\n"
                        + json.dumps(
                            candidate_data,
                            ensure_ascii=False,
                        )
                    ),
                },
            ],
        )
    )

    try:
        result = json.loads(
            response
            .output_text
            .strip()
        )

        ranked_ids = (
            result.get(
                "chunk_ids",
                [],
            )
        )

    except json.JSONDecodeError:
        return candidates[
            :limit
        ]

    candidate_map = {
        item["chunk_id"]: item
        for item in candidates
    }

    reranked = []

    for rank, chunk_id in enumerate(
        ranked_ids,
        start=1,
    ):
        item = (
            candidate_map.get(
                chunk_id
            )
        )

        if not item:
            continue

        ranked_item = dict(
            item
        )

        ranked_item[
            "rerank_rank"
        ] = rank

        reranked.append(
            ranked_item
        )

        if (
            len(reranked)
            >= limit
        ):
            break

    selected_ids = {
        item[
            "chunk_id"
        ]
        for item in reranked
    }

    for candidate in candidates:
        if (
            len(reranked)
            >= limit
        ):
            break

        if (
            candidate[
                "chunk_id"
            ]
            in selected_ids
        ):
            continue

        item = dict(
            candidate
        )

        item[
            "rerank_rank"
        ] = (
            len(
                reranked
            )
            + 1
        )

        reranked.append(
            item
        )

    return reranked


# =========================================================
# RAG Answer
# =========================================================

def generate_answer(
    query: str,
    chunks: list[dict],
    history: list[dict] | None,
) -> str:
    if not chunks:
        return (
            "関連する情報を登録済み文書から"
            "見つけられませんでした。"
        )

    contexts = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        citation_label = (
            _build_citation_label(
                chunk
            )
        )

        source_info = [
            (
                f"Source Number: "
                f"{index}"
            ),
            (
                "Citation Label: "
                f"{citation_label}"
            ),
            (
                "Filename: "
                f"{chunk['filename']}"
            ),
        ]

        if (
            chunk.get(
                "page_number"
            )
            is not None
        ):
            source_info.append(
                (
                    "Page: "
                    f"{chunk['page_number']}"
                )
            )

        if chunk.get(
            "section_title"
        ):
            source_info.append(
                (
                    "Section: "
                    f"{chunk['section_title']}"
                )
            )

        contexts.append(
            (
                f"[Source {index}]\n"
                + "\n".join(
                    source_info
                )
                + "\nContent:\n"
                + chunk[
                    "content"
                ]
            )
        )

    context_text = (
        "\n\n".join(
            contexts
        )
    )

    conversation = (
        _normalize_history(
            history
        )
    )

    response = (
        client.responses.create(
            model=settings.RAG_MODEL,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a RAG assistant. "
                        "Answer in Japanese. "
                        "Use only the provided "
                        "sources as factual evidence. "
                        "Do not invent unsupported "
                        "facts. "
                        "If evidence is insufficient, "
                        "say so. "
                        "For factual claims, cite "
                        "the source using the exact "
                        "Citation Label provided for "
                        "that source. "
                        "Use the exact Citation Label "
                        "character-for-character. "
                        "Do not change square brackets "
                        "[] to Japanese brackets 【】. "
                        "Do not modify the filename "
                        "or section title. "
                        "Do not use [Source N] in the "
                        "final answer. "
                        "Do not invent filenames, "
                        "page numbers, or section "
                        "names."
                    ),
                },
                *conversation,
                {
                    "role": "user",
                    "content": (
                        f"Question:\n"
                        f"{query}\n\n"
                        "Retrieved sources:\n\n"
                        f"{context_text}"
                    ),
                },
            ],
        )
    )

    answer = (
        response
        .output_text
        .strip()
    )

    if not answer:
        return (
            "回答を生成できませんでした。"
        )

    return answer


# =========================================================
# Normal Conversation
# =========================================================

def generate_conversation_answer(
    query: str,
    history: list[dict] | None,
) -> str:
    conversation = (
        _normalize_history(
            history
        )
    )

    response = (
        client.responses.create(
            model=settings.RAG_MODEL,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant. "
                        "Answer in Japanese. "
                        "Use the conversation history "
                        "when the user asks to "
                        "summarize, simplify, "
                        "rephrase, translate, or "
                        "elaborate on a previous "
                        "answer. "
                        "Do not claim to have searched "
                        "documents in this mode."
                    ),
                },
                *conversation,
                {
                    "role": "user",
                    "content": query,
                },
            ],
        )
    )

    answer = (
        response
        .output_text
        .strip()
    )

    if not answer:
        return (
            "回答を生成できませんでした。"
        )

    return answer


# =========================================================
# Citation
# =========================================================

def _build_citation_label(
    chunk: dict,
) -> str:
    filename = (
        chunk[
            "filename"
        ]
    )

    section_title = (
        chunk.get(
            "section_title"
        )
    )

    page_number = (
        chunk.get(
            "page_number"
        )
    )

    parts = [
        filename,
    ]

    if section_title:
        parts.append(
            section_title
        )

    if page_number is not None:
        parts.append(
            f"p.{page_number}"
        )

    return (
        "["
        + " / ".join(
            parts
        )
        + "]"
    )


def _build_source_response(
    index: int,
    chunk: dict,
) -> dict:
    return {
        "source_number": (
            index
        ),
        "citation_label": (
            _build_citation_label(
                chunk
            )
        ),
        "document_id": (
            chunk[
                "document_id"
            ]
        ),
        "chunk_id": (
            chunk[
                "chunk_id"
            ]
        ),
        "chunk_index": (
            chunk[
                "chunk_index"
            ]
        ),
        "filename": (
            chunk[
                "filename"
            ]
        ),
        "page_number": (
            chunk.get(
                "page_number"
            )
        ),
        "section_title": (
            chunk.get(
                "section_title"
            )
        ),
    }


# =========================================================
# History
# =========================================================

def _normalize_history(
    history: list[dict] | None,
) -> list[dict]:
    if not history:
        return []

    result = []

    for item in history:
        role = (
            item.get(
                "role",
                "",
            )
            .strip()
        )

        content = (
            item.get(
                "content",
                "",
            )
            .strip()
        )

        if role not in {
            "user",
            "assistant",
        }:
            continue

        if not content:
            continue

        result.append(
            {
                "role": role,
                "content": (
                    content
                ),
            }
        )

    return result


# =========================================================
# Regex
# =========================================================

def _matches_any(
    text: str,
    patterns: list[str],
) -> bool:
    return any(
        re.match(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern
        in patterns
    )


def _contains_any(
    text: str,
    patterns: list[str],
) -> bool:
    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern
        in patterns
    )