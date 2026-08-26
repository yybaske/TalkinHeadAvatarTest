import os

import psycopg

from dotenv import load_dotenv
from pgvector.psycopg import register_vector


# ============================================================
# 設定
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

EMBEDDING_DIMENSIONS = 1536


if not DATABASE_URL:

    raise RuntimeError(
        "DATABASE_URL が設定されていません。\n"
        ".env に DATABASE_URL を設定してください。"
    )


# ============================================================
# Raw Connection
# ============================================================

def get_raw_connection():

    return psycopg.connect(
        DATABASE_URL
    )


# ============================================================
# Normal Connection
# ============================================================

def get_connection():

    conn = get_raw_connection()

    try:

        register_vector(
            conn
        )

    except Exception:

        conn.close()
        raise

    return conn


# ============================================================
# DB初期化
# ============================================================

def init_database():

    # --------------------------------------------------------
    # pgvector
    # --------------------------------------------------------

    conn = get_raw_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                CREATE EXTENSION IF NOT EXISTS vector
                """
            )

        conn.commit()

    finally:

        conn.close()


    # --------------------------------------------------------
    # Table
    # --------------------------------------------------------

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            # =================================================
            # documents
            # =================================================

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (

                    id BIGSERIAL PRIMARY KEY,

                    filename TEXT NOT NULL,

                    file_hash TEXT NOT NULL,

                    file_size BIGINT NOT NULL,

                    mime_type TEXT,

                    file_data BYTEA NOT NULL,

                    version INTEGER NOT NULL
                        DEFAULT 1,

                    document_type TEXT NOT NULL
                        DEFAULT 'general',

                    status TEXT NOT NULL
                        DEFAULT 'published',

                    is_latest BOOLEAN NOT NULL
                        DEFAULT TRUE,

                    valid_from DATE,

                    valid_to DATE,

                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT NOW(),

                    updated_at TIMESTAMPTZ NOT NULL
                        DEFAULT NOW()

                )
                """
            )


            # =================================================
            # 既存DB移行
            # =================================================

            cur.execute(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS version INTEGER
                NOT NULL DEFAULT 1
                """
            )

            cur.execute(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS document_type TEXT
                NOT NULL DEFAULT 'general'
                """
            )

            cur.execute(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS is_latest BOOLEAN
                NOT NULL DEFAULT TRUE
                """
            )

            cur.execute(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS valid_from DATE
                """
            )

            cur.execute(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS valid_to DATE
                """
            )


            # -------------------------------------------------
            # 旧 UNIQUE(filename) を解除
            #
            # 同一ファイル名で複数Versionを保持するため
            # -------------------------------------------------

            cur.execute(
                """
                ALTER TABLE documents
                DROP CONSTRAINT IF EXISTS documents_filename_key
                """
            )


            # =================================================
            # document_chunks
            # =================================================

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS document_chunks (

                    id BIGSERIAL PRIMARY KEY,

                    document_id BIGINT NOT NULL,

                    page_number INTEGER NOT NULL,

                    chunk_number INTEGER NOT NULL,

                    content TEXT NOT NULL,

                    embedding VECTOR(
                        {EMBEDDING_DIMENSIONS}
                    ) NOT NULL,

                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT NOW(),

                    CONSTRAINT fk_document

                        FOREIGN KEY (
                            document_id
                        )

                        REFERENCES documents(id)

                        ON DELETE CASCADE

                )
                """
            )


            # =================================================
            # Index
            # =================================================

            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                idx_document_chunks_unique

                ON document_chunks (
                    document_id,
                    page_number,
                    chunk_number
                )
                """
            )


            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_document_chunks_document

                ON document_chunks (
                    document_id
                )
                """
            )


            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_documents_search_filter

                ON documents (
                    status,
                    is_latest,
                    document_type,
                    valid_from,
                    valid_to
                )
                """
            )


            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_documents_filename_version

                ON documents (
                    filename,
                    version DESC
                )
                """
            )


            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_document_chunks_embedding_hnsw

                ON document_chunks

                USING hnsw (
                    embedding vector_cosine_ops
                )
                """
            )

        conn.commit()

    finally:

        conn.close()


# ============================================================
# DB Health
# ============================================================

def check_database():

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                "SELECT 1"
            )

            result = cur.fetchone()

            return (
                result is not None
                and result[0] == 1
            )

    finally:

        conn.close()


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    print(
        "DBを初期化しています..."
    )

    init_database()

    print(
        "DB初期化完了"
    )

    print(
        "DB接続:",
        "OK"
        if check_database()
        else "NG",
    )