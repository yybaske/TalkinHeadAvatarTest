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
# 素のDB接続
#
# pgvectorがまだ有効化されていない初期化処理でも
# 使用できる接続
# ============================================================

def get_raw_connection():

    return psycopg.connect(
        DATABASE_URL
    )


# ============================================================
# 通常のDB接続
#
# vector拡張が有効化された後はこちらを使用
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
    # 最初はregister_vector()しない接続を使用
    # --------------------------------------------------------

    conn = get_raw_connection()

    try:

        with conn.cursor() as cur:

            # ================================================
            # pgvector有効化
            # ================================================

            cur.execute(
                """
                CREATE EXTENSION IF NOT EXISTS vector
                """
            )

        conn.commit()

    finally:

        conn.close()


    # --------------------------------------------------------
    # vector拡張有効化後なので、ここから通常接続
    # --------------------------------------------------------

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            # ================================================
            # documents
            # ================================================

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (

                    id BIGSERIAL PRIMARY KEY,

                    filename TEXT NOT NULL UNIQUE,

                    file_hash TEXT NOT NULL,

                    file_size BIGINT NOT NULL,

                    mime_type TEXT,

                    file_data BYTEA NOT NULL,

                    status TEXT NOT NULL
                        DEFAULT 'ready',

                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT NOW(),

                    updated_at TIMESTAMPTZ NOT NULL
                        DEFAULT NOW()

                )
                """
            )


            # ================================================
            # document_chunks
            # ================================================

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


            # ================================================
            # Chunk重複防止
            # ================================================

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


            # ================================================
            # document_id検索用
            # ================================================

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_document_chunks_document

                ON document_chunks (
                    document_id
                )
                """
            )


            # ================================================
            # ベクトル検索用HNSW
            # ================================================

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
# DBヘルスチェック
# ============================================================

def check_database():

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                "SELECT 1"
            )

            result = (
                cur.fetchone()
            )

            return (
                result is not None
                and result[0] == 1
            )

    finally:

        conn.close()


# ============================================================
# pgvector確認
# ============================================================

def check_vector_extension():

    conn = get_raw_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT EXISTS (

                    SELECT 1

                    FROM pg_extension

                    WHERE extname = 'vector'

                )
                """
            )

            result = (
                cur.fetchone()
            )

            return (
                result is not None
                and result[0] is True
            )

    finally:

        conn.close()


# ============================================================
# テーブル確認
# ============================================================

def check_tables():

    conn = get_raw_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    table_name

                FROM information_schema.tables

                WHERE
                    table_schema = 'public'
                    AND table_name IN (
                        'documents',
                        'document_chunks'
                    )

                ORDER BY
                    table_name
                """
            )

            rows = (
                cur.fetchall()
            )

            return [
                row[0]
                for row in rows
            ]

    finally:

        conn.close()


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    print(
        "DBを初期化しています..."
    )

    try:

        init_database()

        print(
            "DB初期化完了"
        )

        print()

        print(
            "pgvector:",
            (
                "OK"
                if check_vector_extension()
                else "NG"
            ),
        )

        tables = check_tables()

        print(
            "作成済みテーブル:",
            ", ".join(tables)
            if tables
            else "なし",
        )

        print(
            "DB接続:",
            (
                "OK"
                if check_database()
                else "NG"
            ),
        )

    except Exception as e:

        print()
        print(
            "DB初期化に失敗しました。"
        )

        print(
            str(e)
        )

        raise