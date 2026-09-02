from fastapi import UploadFile

from app.parsers.document_parser import (
    extract_document,
)
from app.repositories.document_repository import (
    delete_document,
    list_documents,
    save_document,
)
from app.services.chunker import (
    split_document,
)
from app.services.embedding_service import (
    create_embeddings,
)


async def register_document(
    file: UploadFile,
) -> dict:
    parts = await extract_document(
        file
    )

    if not parts:
        raise ValueError(
            "文書からテキストを取得できませんでした。"
        )

    chunks = split_document(
        parts
    )

    if not chunks:
        raise ValueError(
            "チャンクを作成できませんでした。"
        )

    contents = [
        chunk["content"]
        for chunk in chunks
    ]

    embeddings = create_embeddings(
        contents
    )

    document_id = save_document(
        filename=(
            file.filename
            or "unknown"
        ),
        content_type=file.content_type,
        chunks=chunks,
        embeddings=embeddings,
    )

    return {
        "status": "ok",
        "document_id": document_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "chunk_count": len(
            chunks
        ),
        "embedding_dimensions": (
            len(embeddings[0])
            if embeddings
            else 0
        ),
    }


def get_documents() -> dict:
    documents = list_documents()

    return {
        "status": "ok",
        "count": len(documents),
        "documents": documents,
    }


def remove_document(
    document_id: int,
) -> dict:
    deleted = delete_document(
        document_id
    )

    if not deleted:
        raise ValueError(
            f"document_id={document_id} "
            "の文書は存在しません。"
        )

    return {
        "status": "ok",
        "document_id": document_id,
        "message": "文書を削除しました。",
    }