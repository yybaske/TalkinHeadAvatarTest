from pathlib import Path

import streamlit as st

from rag import (
    sync_documents,
    search,
    generate_answer,
    delete_document,
)


# ============================================================
# 設定
# ============================================================

DOCS_DIR = Path("./docs")

DOCS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Streamlit設定
# ============================================================

st.set_page_config(
    page_title="RAG Assistant",
    page_icon="🔎",
    layout="wide",
)


# ============================================================
# Session State 初期化
# ============================================================

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None


# ============================================================
# 削除処理
#
# 画面を描画する前に実施する。
# 削除ボタン押下中に直接ファイル削除すると、
# Streamlitの再描画タイミングで表示崩れが起きやすいため。
# ============================================================

if st.session_state.pending_delete:

    source = st.session_state.pending_delete

    try:

        delete_document(
            source
        )

        # RAGキャッシュを破棄
        st.cache_resource.clear()

        # 削除済みPDFを参照している過去のチャット履歴もクリア
        st.session_state.messages = []

        st.session_state.delete_success = (
            f"{source} を削除しました。"
        )

    except Exception as e:

        st.session_state.delete_error = (
            f"{source} の削除に失敗しました。\n\n{e}"
        )

    finally:

        st.session_state.pending_delete = None

        st.rerun()


# ============================================================
# タイトル
# ============================================================

st.title(
    "🔎 RAG Assistant"
)

st.caption(
    "PDFを登録して、資料の内容について質問できます。"
)


# ============================================================
# RAG初期化
# ============================================================

@st.cache_resource
def initialize_rag():

    return sync_documents()


try:

    index, chunks = initialize_rag()

except RuntimeError:

    # PDF未登録の場合
    index = None
    chunks = []

except Exception as e:

    st.error(
        f"RAGの初期化に失敗しました。\n\n{e}"
    )

    st.stop()


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.header(
        "📚 ドキュメント管理"
    )


    # ========================================================
    # 各種メッセージ
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
    # PDFアップロード
    # ========================================================

    uploaded_files = st.file_uploader(
        "PDFをアップロード",
        type=["pdf"],
        accept_multiple_files=True,
        key=(
            "pdf_uploader_"
            f"{st.session_state.uploader_key}"
        ),
    )


    # ========================================================
    # PDF登録
    # ========================================================

    if uploaded_files:

        if st.button(
            "📥 RAGへ登録",
            use_container_width=True,
            type="primary",
        ):

            saved_files = []

            # ------------------------------------------------
            # PDF保存
            # ------------------------------------------------

            try:

                for uploaded_file in uploaded_files:

                    safe_name = Path(
                        uploaded_file.name
                    ).name

                    file_path = (
                        DOCS_DIR
                        / safe_name
                    )

                    with open(
                        file_path,
                        "wb",
                    ) as f:

                        f.write(
                            uploaded_file.getbuffer()
                        )

                    saved_files.append(
                        safe_name
                    )

            except Exception as e:

                st.error(
                    f"PDFの保存に失敗しました。\n\n{e}"
                )

                st.stop()


            # ------------------------------------------------
            # RAG登録処理
            # ------------------------------------------------

            with st.status(
                "PDFをRAGへ登録しています...",
                expanded=True,
            ) as status:

                progress_bar = st.progress(
                    0,
                    text="処理を開始しています...",
                )

                phase_text = st.empty()
                detail_text = st.empty()


                # ============================================
                # Progress Callback
                # ============================================

                def update_progress(
                    phase,
                    current,
                    total,
                    message,
                ):

                    if phase == "scan":

                        base = 0
                        width = 5
                        phase_name = "① PDF確認"

                    elif phase == "pdf":

                        base = 5
                        width = 20
                        phase_name = "② PDF解析"

                    elif phase == "chunk":

                        base = 25
                        width = 10
                        phase_name = "③ Chunk作成"

                    elif phase == "embedding":

                        base = 35
                        width = 55
                        phase_name = "④ Embedding生成"

                    elif phase == "index":

                        base = 90
                        width = 9
                        phase_name = "⑤ 検索Index更新"

                    elif phase == "complete":

                        base = 100
                        width = 0
                        phase_name = "⑥ 完了"

                    else:

                        base = 0
                        width = 0
                        phase_name = "処理中"


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
                            + (
                                width
                                * ratio
                            )
                        )


                    percent = max(
                        0,
                        min(
                            percent,
                            100,
                        ),
                    )


                    progress_bar.progress(
                        percent,
                        text=(
                            f"{percent}% - {message}"
                        ),
                    )

                    phase_text.markdown(
                        f"**{phase_name}**"
                    )

                    detail_text.caption(
                        message
                    )


                # ============================================
                # RAG更新
                # ============================================

                try:

                    st.cache_resource.clear()

                    index, chunks = sync_documents(
                        progress_callback=update_progress
                    )

                    progress_bar.progress(
                        100,
                        text="100% - 登録完了",
                    )

                    phase_text.markdown(
                        "**⑥ 完了**"
                    )

                    detail_text.caption(
                        (
                            f"{len(saved_files)}件のPDFを"
                            "RAGへ登録しました。"
                        )
                    )

                    status.update(
                        label=(
                            "PDFのRAG登録が完了しました。"
                        ),
                        state="complete",
                        expanded=False,
                    )

                except Exception as e:

                    status.update(
                        label=(
                            "PDFのRAG登録に失敗しました。"
                        ),
                        state="error",
                        expanded=True,
                    )

                    st.error(
                        str(e)
                    )

                    st.stop()


            # ------------------------------------------------
            # FileUploaderリセット
            # ------------------------------------------------

            st.session_state.uploader_key += 1

            st.session_state.upload_success = (
                f"{len(saved_files)}件のPDFを登録しました。"
            )

            st.rerun()


    # ========================================================
    # RAG情報
    # ========================================================

    st.divider()

    st.subheader(
        "RAG情報"
    )


    # 実ファイルを正として表示する
    source_files = sorted(
        pdf.name
        for pdf in DOCS_DIR.glob("*.pdf")
    )


    st.metric(
        "登録PDF数",
        len(source_files),
    )

    st.metric(
        "登録Chunk数",
        len(chunks),
    )


    # ========================================================
    # 登録資料
    # ========================================================

    st.divider()

    st.subheader(
        "登録資料"
    )


    if source_files:

        for source in source_files:

            col1, col2 = st.columns(
                [5, 1],
                vertical_alignment="center",
            )

            with col1:

                st.write(
                    f"📄 {source}"
                )

            with col2:

                if st.button(
                    "🗑️",
                    key=f"delete_{source}",
                    help=f"{source} を削除",
                    use_container_width=True,
                ):

                    # ここでは削除しない
                    # 次回rerun冒頭で削除する
                    st.session_state.pending_delete = source

                    st.rerun()

    else:

        st.caption(
            "PDFが登録されていません。"
        )


    # ========================================================
    # 手動再読み込み
    # ========================================================

    st.divider()

    if st.button(
        "🔄 RAGを再読み込み",
        use_container_width=True,
    ):

        st.cache_resource.clear()

        st.rerun()


# ============================================================
# チャット履歴表示
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

- Page: {source["page"]}
- 類似度: `{source["score"]:.4f}`
"""
                    )


# ============================================================
# PDF未登録
# ============================================================

if index is None:

    st.info(
        "左側のメニューからPDFをアップロードしてください。"
    )

    st.stop()


# ============================================================
# 質問入力
# ============================================================

question = st.chat_input(
    "資料について質問してください"
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

        with st.status(
            "回答を作成しています...",
            expanded=True,
        ) as answer_status:

            search_status = st.empty()

            search_status.write(
                "🔎 関連する資料を検索しています..."
            )

            try:

                # -------------------------------------------
                # Vector検索
                # -------------------------------------------

                results = search(
                    question,
                    index,
                    chunks,
                )

                search_status.write(
                    (
                        f"✅ 関連資料を"
                        f"{len(results)}件取得しました。"
                    )
                )

                llm_status = st.empty()

                llm_status.write(
                    "🤖 回答を生成しています..."
                )


                # -------------------------------------------
                # LLM
                # -------------------------------------------

                answer = generate_answer(
                    question,
                    results,
                )

                llm_status.write(
                    "✅ 回答生成完了"
                )

                answer_status.update(
                    label="回答を生成しました。",
                    state="complete",
                    expanded=False,
                )

            except Exception as e:

                answer_status.update(
                    label="回答生成に失敗しました。",
                    state="error",
                    expanded=True,
                )

                st.error(
                    str(e)
                )

                st.stop()


        # ====================================================
        # 回答表示
        # ====================================================

        st.markdown(
            answer
        )


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
            "content": answer,
            "sources": results,
        }
    )