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
    generate_speech_text,
)

from speech import (
    text_to_speech,
    cleanup_audio_files,
)

from lipsync import (
    start_lipsync,
    LIPSYNC_ENABLED,
)


# ============================================================
# Streamlit設定
# ============================================================

st.set_page_config(
    page_title="RAG Avatar Assistant",
    page_icon="🤖",
    layout="wide",
)


# ============================================================
# Session State
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None

if "speech_enabled" not in st.session_state:
    st.session_state.speech_enabled = True


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

if st.session_state.pending_delete is not None:

    document_id = (
        st.session_state.pending_delete
    )

    try:

        filename = delete_document(
            document_id
        )

        # 過去回答に削除済み文書の参照が残らないようにする
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
# タイトル
# ============================================================

st.title(
    "🤖 RAG Avatar Assistant"
)

st.caption(
    "PostgreSQL + pgvector + OpenAI + TTS + LipSync"
)


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.header(
        "📚 ドキュメント管理"
    )


    # ========================================================
    # メッセージ
    # ========================================================

    if "upload_success" in st.session_state:

        st.success(
            st.session_state.upload_success
        )

        del st.session_state.upload_success


    if "delete_success" in st.session_state:

        st.success(
            st.session_state.delete_success
        )

        del st.session_state.delete_success


    if "delete_error" in st.session_state:

        st.error(
            st.session_state.delete_error
        )

        del st.session_state.delete_error


    # ========================================================
    # DB接続状態
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


    # ========================================================
    # 音声 / LipSync
    # ========================================================

    st.divider()

    st.subheader(
        "🔊 音声・アバター"
    )


    st.session_state.speech_enabled = (
        st.toggle(
            "回答を音声化",
            value=(
                st.session_state.speech_enabled
            ),
        )
    )


    if LIPSYNC_ENABLED:

        st.caption(
            "🟢 LipSync 有効"
        )

    else:

        st.caption(
            "⚪ LipSync 無効"
        )


    st.divider()


    # ========================================================
    # PDFアップロード
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
    # PDF登録
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
                # Progress Callback
                # ============================================

                def update_progress(
                    phase,
                    current,
                    total,
                    message,
                ):

                    settings = {

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
                    ) = settings.get(
                        phase,
                        (
                            0,
                            0,
                            "処理中",
                        ),
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

                    for (
                        file_number,
                        uploaded_file,
                    ) in enumerate(
                        uploaded_files,
                        start=1,
                    ):

                        phase_area.markdown(
                            (
                                f"### "
                                f"{file_number}"
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


            # ================================================
            # FileUploaderリセット
            # ================================================

            st.session_state.uploader_key += 1


            st.session_state.upload_success = (
                f"{len(uploaded_files)}件の"
                "処理が完了しました。"
            )


            st.rerun()


    # ========================================================
    # 登録資料
    # ========================================================

    st.divider()


    documents = (
        get_documents()
    )


    total_chunks = sum(
        document["chunk_count"]
        for document in documents
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
    # 登録資料一覧
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
                    (
                        f"**📄 "
                        f"{document['filename']}**"
                    )
                )


                size_mb = (
                    document["file_size"]
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
# チャット履歴
# ============================================================

for message in st.session_state.messages:

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

                for source in message["sources"]:

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
# 質問
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

        # ====================================================
        # 状態表示
        # ====================================================

        progress_container = (
            st.container(
                border=True
            )
        )


        with progress_container:

            st.markdown(
                "### 🔄 RAG処理"
            )


            search_line = (
                st.empty()
            )

            generation_line = (
                st.empty()
            )

            speech_line = (
                st.empty()
            )

            lipsync_line = (
                st.empty()
            )


        # ====================================================
        # STEP 1
        # pgvector検索
        # ====================================================

        search_line.markdown(
            "🔎 **pgvectorで関連資料を検索しています...**"
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


        # ====================================================
        # STEP 2
        # LLM Streaming
        # ====================================================

        generation_line.markdown(
            "🤖 **回答を生成しています...**"
        )


        answer_placeholder = (
            st.empty()
        )


        full_answer = ""


        try:

            for delta in (
                generate_answer_stream(
                    question,
                    results,
                )
            ):

                full_answer += delta


                # ============================================
                # 回答はリアルタイム表示
                # ============================================

                answer_placeholder.markdown(
                    full_answer
                    + " ▌"
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
        # 回答生成完了
        # ====================================================

        answer_placeholder.markdown(
            full_answer
        )


        generation_line.markdown(
            "✅ **回答生成完了**"
        )


        # ====================================================
        # STEP 3
        # 音声用の話し言葉へ変換
        # ====================================================

        audio_path = None
        speech_text = ""


        if (
            st.session_state
            .speech_enabled
            and full_answer.strip()
        ):

            speech_line.markdown(
                "🗣️ **話し言葉に変換しています...**"
            )


            try:

                # ====================================================
                # 表示用回答
                #        ↓
                # アバター発話用の口語へ変換
                # ====================================================

                speech_text = (
                    generate_speech_text(
                        full_answer
                    )
                )


                speech_line.markdown(
                    "🔊 **音声を生成しています...**"
                )


                # ====================================================
                # TTS
                # ====================================================

                audio_path = (
                    text_to_speech(
                        speech_text
                    )
                )


                speech_line.markdown(
                    "✅ **音声生成完了**"
                )


                # ====================================================
                # Browser再生
                # ====================================================

                st.audio(
                    str(audio_path),
                    format="audio/wav",
                    autoplay=True,
                )


            except Exception as e:

                speech_line.markdown(
                    "❌ **音声生成に失敗しました**"
                )

                st.warning(
                    str(e)
                )


        # ====================================================
        # STEP 4
        # LipSync
        #
        # ★ ここも1回答につき1回だけ
        # ====================================================

        if (
            audio_path is not None
            and LIPSYNC_ENABLED
        ):

            lipsync_line.markdown(
                "👄 **LipSync動画を生成しています...**"
            )


            try:

                start_lipsync(
                    audio_path,
                    speech_text,
                )


                lipsync_line.markdown(
                    "✅ **LipSync処理を開始しました**"
                )


            except Exception as e:

                lipsync_line.markdown(
                    "❌ **LipSync処理に失敗しました**"
                )

                st.warning(
                    str(e)
                )


        # ====================================================
        # 参照資料
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


                text = result["text"]


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
    # 履歴保存
    # ========================================================

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": full_answer,
            "sources": results,
        }
    )


# ============================================================
# 古い音声削除
# ============================================================

cleanup_audio_files(
    keep_latest=10
)