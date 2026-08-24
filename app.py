import streamlit as st

from db import (
    init_database,
    check_database,
)

from rag import (
    get_documents,
    register_document,
    delete_document,
    search,
    generate_answer_stream,
)


# ============================================================
# Streamlit
# ============================================================

st.set_page_config(
    page_title="RAG Assistant",
    page_icon="🔎",
    layout="wide",
)


# ============================================================
# Session
# ============================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


if "uploader_key" not in st.session_state:

    st.session_state.uploader_key = 0


if "pending_delete" not in st.session_state:

    st.session_state.pending_delete = None


# ============================================================
# DB初期化
# ============================================================

try:

    init_database()

except Exception as e:

    st.error(
        "PostgreSQLへ接続できません。"
    )

    st.code(
        str(e)
    )

    st.stop()


# ============================================================
# 削除処理
# ============================================================

if (
    st.session_state
    .pending_delete
    is not None
):

    document_id = (
        st.session_state
        .pending_delete
    )

    try:

        filename = delete_document(
            document_id
        )

        st.session_state.messages = []

        st.session_state.delete_success = (
            f"{filename} を削除しました。"
        )

    except Exception as e:

        st.session_state.delete_error = (
            str(e)
        )

    finally:

        st.session_state.pending_delete = None

        st.rerun()


# ============================================================
# Title
# ============================================================

st.title(
    "🔎 RAG Assistant"
)

st.caption(
    "PostgreSQL + pgvector を利用した"
    "ドキュメント検索RAG"
)


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.header(
        "📚 ドキュメント管理"
    )


    # ========================================================
    # Messages
    # ========================================================

    if "upload_success" in st.session_state:

        st.success(
            st.session_state.upload_success
        )

        del (
            st.session_state.upload_success
        )


    if "delete_success" in st.session_state:

        st.success(
            st.session_state.delete_success
        )

        del (
            st.session_state.delete_success
        )


    if "delete_error" in st.session_state:

        st.error(
            st.session_state.delete_error
        )

        del (
            st.session_state.delete_error
        )


    # ========================================================
    # DB状態
    # ========================================================

    try:

        db_ok = (
            check_database()
        )

    except Exception:

        db_ok = False


    if db_ok:

        st.caption(
            "🟢 PostgreSQL 接続中"
        )

    else:

        st.caption(
            "🔴 PostgreSQL 接続エラー"
        )


    st.divider()


    # ========================================================
    # Upload
    # ========================================================

    uploaded_files = (
        st.file_uploader(
            "PDFをアップロード",
            type=[
                "pdf",
            ],
            accept_multiple_files=True,
            key=(
                "pdf_uploader_"
                f"{st.session_state.uploader_key}"
            ),
        )
    )


    # ========================================================
    # Register
    # ========================================================

    if uploaded_files:

        if st.button(
            "📥 RAGへ登録",
            type="primary",
            use_container_width=True,
        ):

            with st.status(
                "PDFを登録しています...",
                expanded=True,
            ) as status:

                progress_bar = (
                    st.progress(
                        0,
                        text=(
                            "処理を開始しています..."
                        ),
                    )
                )

                phase_area = (
                    st.empty()
                )

                detail_area = (
                    st.empty()
                )


                # ============================================
                # Callback
                # ============================================

                def update_progress(
                    phase,
                    current,
                    total,
                    message,
                ):

                    phase_settings = {

                        "scan": (
                            0,
                            5,
                            "① ファイル確認"
                        ),

                        "pdf": (
                            5,
                            20,
                            "② PDF解析"
                        ),

                        "chunk": (
                            25,
                            10,
                            "③ Chunk作成"
                        ),

                        "embedding": (
                            35,
                            50,
                            "④ Embedding生成"
                        ),

                        "database": (
                            85,
                            14,
                            "⑤ DB保存"
                        ),

                        "complete": (
                            100,
                            0,
                            "⑥ 完了"
                        ),
                    }


                    (
                        base,
                        width,
                        phase_name,
                    ) = (
                        phase_settings
                        .get(
                            phase,
                            (
                                0,
                                0,
                                "処理中",
                            ),
                        )
                    )


                    if (
                        total is not None
                        and total > 0
                    ):

                        ratio = (
                            current
                            / total
                        )

                    else:

                        ratio = 0


                    ratio = max(
                        0,
                        min(
                            ratio,
                            1,
                        ),
                    )


                    if phase == "complete":

                        percent = 100

                    else:

                        percent = int(
                            base
                            + width
                            * ratio
                        )


                    progress_bar.progress(
                        percent,
                        text=(
                            f"{percent}% - "
                            f"{message}"
                        ),
                    )


                    phase_area.markdown(
                        f"**{phase_name}**"
                    )


                    detail_area.caption(
                        message
                    )


                # ============================================
                # 登録処理
                # ============================================

                try:

                    for file_number, uploaded_file in enumerate(
                        uploaded_files,
                        start=1,
                    ):

                        phase_area.markdown(
                            (
                                f"### {file_number}"
                                f"/{len(uploaded_files)} "
                                f"{uploaded_file.name}"
                            )
                        )


                        register_document(
                            filename=(
                                uploaded_file.name
                            ),

                            file_bytes=(
                                uploaded_file
                                .getvalue()
                            ),

                            mime_type=(
                                uploaded_file.type
                                or "application/pdf"
                            ),

                            progress_callback=(
                                update_progress
                            ),
                        )


                    progress_bar.progress(
                        100,
                        text=(
                            "100% - 登録完了"
                        ),
                    )


                    status.update(
                        label=(
                            "PDF登録が完了しました。"
                        ),
                        state="complete",
                        expanded=False,
                    )


                except Exception as e:

                    status.update(
                        label=(
                            "PDF登録に失敗しました。"
                        ),
                        state="error",
                        expanded=True,
                    )

                    st.error(
                        str(e)
                    )

                    st.stop()


            st.session_state.uploader_key += 1


            st.session_state.upload_success = (
                f"{len(uploaded_files)}件の"
                "処理が完了しました。"
            )


            st.rerun()


    # ========================================================
    # Documents
    # ========================================================

    st.divider()

    documents = (
        get_documents()
    )


    total_chunks = sum(
        doc["chunk_count"]
        for doc in documents
    )


    col1, col2 = st.columns(
        2
    )


    with col1:

        st.metric(
            "登録PDF数",
            len(documents),
        )


    with col2:

        st.metric(
            "Chunk数",
            total_chunks,
        )


    st.divider()


    st.subheader(
        "登録資料"
    )


    if not documents:

        st.caption(
            "資料が登録されていません。"
        )


    # ========================================================
    # Document list
    # ========================================================

    for document in documents:

        container = (
            st.container(
                border=True
            )
        )


        with container:

            col1, col2 = (
                st.columns(
                    [
                        5,
                        1,
                    ],
                    vertical_alignment=(
                        "center"
                    ),
                )
            )


            with col1:

                st.markdown(
                    f"**📄 "
                    f"{document['filename']}**"
                )


                size_mb = (
                    document[
                        "file_size"
                    ]
                    / 1024
                    / 1024
                )


                st.caption(
                    (
                        f"{size_mb:.2f} MB"
                        f" / "
                        f"{document['chunk_count']} Chunk"
                    )
                )


            with col2:

                if st.button(
                    "🗑️",
                    key=(
                        "delete_"
                        f"{document['id']}"
                    ),
                    help=(
                        f"{document['filename']}"
                        " を削除"
                    ),
                    use_container_width=True,
                ):

                    st.session_state.pending_delete = (
                        document["id"]
                    )

                    st.rerun()


# ============================================================
# Chat history
# ============================================================

for message in (
    st.session_state.messages
):

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


        if "sources" in message:

            with st.expander(
                "📚 参照資料"
            ):

                for source in (
                    message["sources"]
                ):

                    st.markdown(
                        f"""
**📄 {source["source"]}**

Page: {source["page"]}

類似度: `{source["score"]:.4f}`
"""
                    )


# ============================================================
# 文書なし
# ============================================================

if not documents:

    st.info(
        "左側からPDFを登録してください。"
    )

    st.stop()


# ============================================================
# Chat
# ============================================================

question = (
    st.chat_input(
        "資料について質問してください"
    )
)


if question:

    # ========================================================
    # User
    # ========================================================

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )


    with st.chat_message(
        "user"
    ):

        st.markdown(
            question
        )


    # ========================================================
    # Assistant
    # ========================================================

    with st.chat_message(
        "assistant"
    ):

        # ----------------------------------------------------
        # 進捗エリア
        # ----------------------------------------------------

        progress_container = (
            st.container(
                border=True
            )
        )


        with progress_container:

            st.markdown(
                "### 🔄 RAG処理中"
            )

            search_line = (
                st.empty()
            )

            context_line = (
                st.empty()
            )

            generation_line = (
                st.empty()
            )


            # =================================================
            # Step 1 検索
            # =================================================

            search_line.markdown(
                "🔎 **関連資料を検索しています...**"
            )


            try:

                results = search(
                    question
                )

            except Exception as e:

                search_line.markdown(
                    "❌ **資料検索に失敗しました**"
                )

                st.error(
                    str(e)
                )

                st.stop()


            search_line.markdown(
                (
                    "✅ **関連資料を検索しました** "
                    f"（{len(results)}件）"
                )
            )


            # =================================================
            # Step 2 Context
            # =================================================

            context_line.markdown(
                "📚 **検索結果を回答用に整理しています...**"
            )


            # ここは軽い処理なので即時完了
            context_line.markdown(
                (
                    "✅ **回答に使用する資料を準備しました** "
                    f"（{len(results)} Chunk）"
                )
            )


            # =================================================
            # Step 3 LLM
            # =================================================

            generation_line.markdown(
                "🤖 **回答を生成しています...**"
            )


        # ----------------------------------------------------
        # 回答を表示する場所
        # ----------------------------------------------------

        answer_placeholder = (
            st.empty()
        )


        full_answer = ""


        try:

            # =================================================
            # ストリーミング生成
            # =================================================

            for delta in (
                generate_answer_stream(
                    question,
                    results,
                )
            ):

                full_answer += (
                    delta
                )

                # カーソル表示
                answer_placeholder.markdown(
                    full_answer
                    + " ▌"
                )


            # =================================================
            # 最終表示
            # =================================================

            answer_placeholder.markdown(
                full_answer
            )


            generation_line.markdown(
                "✅ **回答生成完了**"
            )


        except Exception as e:

            generation_line.markdown(
                "❌ **回答生成に失敗しました**"
            )

            st.error(
                str(e)
            )

            st.stop()


        # ====================================================
        # 出典
        # ====================================================

        with st.expander(
            "📚 参照資料"
        ):

            for result in results:

                st.markdown(
                    f"""
### 📄 {result["source"]}

**Page:** {result["page"]}

**類似度:** `{result["score"]:.4f}`
"""
                )

                text = (
                    result["text"]
                )

                if len(text) > 500:

                    text = (
                        text[:500]
                        + "..."
                    )

                st.caption(
                    text
                )

                st.divider()


    # ========================================================
    # History
    # ========================================================

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": full_answer,
            "sources": results,
        }
    )