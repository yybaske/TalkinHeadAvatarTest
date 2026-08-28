from pydantic import BaseModel
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)

from answer_generator import generate_answer
from chunker import split_text
from db import (
    check_connection,
    hybrid_search,
    save_document,
)
from document_parser import extract_text
from embedding import (
    create_embedding,
    create_embeddings,
)
from query_rewriter import rewrite_query
from reranker import rerank_chunks


app = FastAPI(
    title="RAG API",
    version="0.6.0",
)


class HistoryItem(BaseModel):
    role: str
    content: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    history: list[HistoryItem] = []


class ChatRequest(BaseModel):
    query: str
    history: list[HistoryItem] = []


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.get("/health/db")
def health_db():
    try:
        version = check_connection()

        return {
            "status": "ok",
            "database": "connected",
            "version": version,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
):
    try:
        text = await extract_text(file)

        if not text.strip():
            raise ValueError(
                "文書からテキストを取得できませんでした。"
            )

        chunks = split_text(text)

        if not chunks:
            raise ValueError(
                "チャンクを作成できませんでした。"
            )

        embeddings = create_embeddings(
            chunks
        )

        document_id = save_document(
            filename=file.filename or "unknown",
            content_type=file.content_type,
            chunks=chunks,
            embeddings=embeddings,
        )

        return {
            "status": "ok",
            "document_id": document_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "text_length": len(text),
            "chunk_count": len(chunks),
            "embedding_dimensions": (
                len(embeddings[0])
                if embeddings
                else 0
            ),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/search")
def search(
    request: SearchRequest,
):
    try:
        original_query = (
            request.query.strip()
        )

        if not original_query:
            raise ValueError(
                "検索文字列を入力してください。"
            )

        if request.limit < 1:
            raise ValueError(
                "limitは1以上で指定してください。"
            )

        if request.limit > 20:
            raise ValueError(
                "limitは20以下で指定してください。"
            )

        history = [
            item.model_dump()
            for item in request.history
        ]

        # ------------------------------------------
        # Query Rewrite
        # ------------------------------------------

        search_query = rewrite_query(
            query=original_query,
            history=history,
        )

        # ------------------------------------------
        # Embedding
        # ------------------------------------------

        query_embedding = create_embedding(
            search_query
        )

        # ------------------------------------------
        # Hybrid Search
        # ------------------------------------------

        candidates = hybrid_search(
            query=search_query,
            embedding=query_embedding,
            limit=20,
            candidate_limit=30,
        )

        # ------------------------------------------
        # Rerank
        # ------------------------------------------

        results = rerank_chunks(
            query=search_query,
            candidates=candidates,
            limit=request.limit,
        )

        return {
            "status": "ok",
            "search_type": "hybrid_rerank",
            "original_query": original_query,
            "search_query": search_query,
            "history_count": len(history),
            "candidate_count": len(candidates),
            "count": len(results),
            "results": results,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/chat")
def chat(
    request: ChatRequest,
):
    try:
        original_query = (
            request.query.strip()
        )

        if not original_query:
            raise ValueError(
                "質問を入力してください。"
            )

        history = [
            item.model_dump()
            for item in request.history
        ]

        # ==========================================
        # 1. Query Rewrite
        # ==========================================

        search_query = rewrite_query(
            query=original_query,
            history=history,
        )

        # ==========================================
        # 2. Query Embedding
        # ==========================================

        query_embedding = create_embedding(
            search_query
        )

        # ==========================================
        # 3. Hybrid Search
        #
        # Rerank用に20件取得
        # ==========================================

        candidates = hybrid_search(
            query=search_query,
            embedding=query_embedding,
            limit=20,
            candidate_limit=30,
        )

        # ==========================================
        # 4. Rerank
        #
        # 回答生成には上位5件のみ使用
        # ==========================================

        chunks = rerank_chunks(
            query=search_query,
            candidates=candidates,
            limit=5,
        )

        # ==========================================
        # 5. Answer Generation
        # ==========================================

        answer = generate_answer(
            query=original_query,
            chunks=chunks,
            history=history,
        )

        # ==========================================
        # 6. Source情報
        # ==========================================

        sources = []

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):
            sources.append(
                {
                    "source_number": index,
                    "document_id": chunk[
                        "document_id"
                    ],
                    "chunk_id": chunk[
                        "chunk_id"
                    ],
                    "chunk_index": chunk[
                        "chunk_index"
                    ],
                    "filename": chunk[
                        "filename"
                    ],
                }
            )

        return {
            "status": "ok",
            "original_query": original_query,
            "search_query": search_query,
            "answer": answer,
            "sources": sources,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )