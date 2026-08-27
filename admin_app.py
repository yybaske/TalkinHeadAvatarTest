from datetime import date, timedelta

import streamlit as st

from db import (
    init_database,
    check_database,
)

from rag import (
    get_documents,
    register_document,
    delete_document,
)


# ============================================================
# Page
# ============================================================

st.set_page_config(
    page_title="Sales AI Admin",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

/* ==========================================================
   Streamlit標準UI
========================================================== */

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}

[data-testid="stSidebar"] {
    display: none;
}

.block-container {
    max-width: 1600px;
    padding-top: 1.5rem;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-bottom: 3rem;
}


/* ==========================================================
   Header
========================================================== */

.admin-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    padding: 20px 24px;

    border: 1px solid rgba(128,128,128,0.20);
    border-radius: 16px;

    margin-bottom: 20px;
}


.admin-header-left {
    display: flex;
    flex-direction: column;
}


.admin-title {
    font-size: 28px;
    font-weight: 700;
    line-height: 1.2;
}


.admin-subtitle {
    margin-top: 6px;

    font-size: 14px;

    opacity: 0.70;
}


.admin-online {
    display: inline-flex;
    align-items: center;
    gap: 7px;

    padding: 7px 12px;

    border-radius: 999px;

    background: rgba(50, 180, 100, 0.10);

    font-size: 13px;
}


.online-dot {
    width: 9px;
    height: 9px;

    border-radius: 50%;

    background: #39b972;
}


/* ==========================================================
   Section
========================================================== */

.section-card {
    border: 1px solid rgba(128,128,128,0.18);
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 18px;
}


.section-title {
    font-size: 20px;
    font-weight: 650;
    margin-bottom: 4px;
}


.section-subtitle {
    font-size: 13px;
    opacity: 0.65;
}


/* ==========================================================
   Document badge
========================================================== */

.doc-badge {
    display: inline-block;

    padding: 5px 10px;

    border-radius: 999px;

    background: rgba(128,128,128,0.08);

    font-size: 12px;
}


/* ==========================================================
   Tabs
========================================================== */

button[data-baseweb="tab"] {
    font-size: 15px;
}


/* ==========================================================
   Metrics
========================================================== */

[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,0.15);
    border-radius: 14px;
    padding: 14px;
}


/* ==========================================================
   Responsive
========================================================== */

@media (max-width: 900px) {

    .admin-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 12px;
    }

}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# Session
# ============================================================

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None


# ============================================================
# DB
# ============================================================

try:

    init_database()

    db_ok = check_database()

except Exception:

    db_ok = False


if not db_ok:

    st.error(
        "PostgreSQLへ接続できません。"
    )

    st.stop()


# ============================================================
# Delete
# ============================================================

if (
    st.session_state.pending_delete
    is not None
):

    try:

        deleted_name = delete_document(
            st.session_state.pending_delete
        )

        st.session_state.delete_success = (
            f"{deleted_name} を削除しました。"
        )

    except Exception as e:

        st.session_state.delete_error = (
            str(e)
        )

    finally:

        st.session_state.pending_delete = None

        st.rerun()


# ============================================================
# Header
# ============================================================

st.markdown(
    """
<div class="admin-header">
<div class="admin-header-left">
<div class="admin-title">⚙️ Sales AI 管理画面</div>
<div class="admin-subtitle">
AIが参照するナレッジの登録・版管理・有効期間を管理します。
</div>
</div>

<div class="admin-online">
<span class="online-dot"></span>
PostgreSQL / pgvector 接続中
</div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# Notification
# ============================================================

if "upload_success" in st.session_state:

    st.success(
        st.session_state.upload_success
    )

    del st.session_state.upload_success


if "upload_info" in st.session_state:

    st.info(
        st.session_state.upload_info
    )

    del st.session_state.upload_info


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


# ============================================================
# Overview
# ============================================================

all_documents = get_documents(
    include_history=True
)


latest_documents = get_documents(
    include_history=False
)


history_documents = [
    document
    for document in all_documents
    if not document[
        "is_latest"
    ]
]


total_chunks = sum(
    document[
        "chunk_count"
    ]
    for document in latest_documents
)


metric1, metric2, metric3 = st.columns(
    3
)


with metric1:

    st.metric(
        "最新資料数",
        len(
            latest_documents
        ),
    )


with metric2:

    st.metric(
        "旧Version数",
        len(
            history_documents
        ),
    )


with metric3:

    st.metric(
        "検索対象Chunk数",
        total_chunks,
    )


st.divider()


# ============================================================
# Tabs
# ============================================================

tab_upload, tab_documents, tab_history = st.tabs(
    [
        "📥 資料登録",
        "📚 最新資料",
        "🕘 Version履歴",
    ]
)


# ============================================================
# Upload Tab
# ============================================================

with tab_upload:

    st.markdown(
        """
<div class="section-card">
<div class="section-title">資料を登録</div>
<div class="section-subtitle">
PDF、Word、Excel、PowerPoint、TXTなどをAIの検索対象として登録します。
</div>
</div>
""",
        unsafe_allow_html=True,
    )


    # ========================================================
    # Metadata
    # ========================================================

    col1, col2 = st.columns(
        2
    )


    with col1:

        document_type = st.selectbox(
            "資料種別",
            options=[
                "general",
                "product",
                "sales_talk",
                "faq",
                "pricing",
                "competitor",
                "case_study",
            ],
            format_func=lambda value: {
                "general": "一般資料",
                "product": "製品資料",
                "sales_talk": "営業トーク",
                "faq": "FAQ",
                "pricing": "価格資料",
                "competitor": "競合比較",
                "case_study": "導入・成功事例",
            }[
                value
            ],
        )


    with col2:

        status = st.selectbox(
            "公開状態",
            options=[
                "published",
                "draft",
            ],
            format_func=lambda value: (
                "公開"
                if value
                == "published"
                else "下書き"
            ),
        )


    col3, col4 = st.columns(
        2
    )


    with col3:

        use_valid_from = st.checkbox(
            "有効開始日を設定"
        )


        valid_from = None


        if use_valid_from:

            valid_from = st.date_input(
                "有効開始日",
                value=date.today(),
            )


    with col4:

        use_valid_to = st.checkbox(
            "有効終了日を設定"
        )


        valid_to = None


        if use_valid_to:

            valid_to = st.date_input(
                "有効終了日",
                value=(
                    date.today()
                    + timedelta(
                        days=365
                    )
                ),
            )


    # ========================================================
    # Uploader
    # ========================================================

    uploaded_files = st.file_uploader(
        "資料をアップロード",
        type=[
            "pdf",
            "txt",
            "md",
            "docx",
            "xlsx",
            "pptx",
            "csv",
            "html",
            "htm",
            "json",
        ],
        accept_multiple_files=True,
        key=(
            "admin_uploader_"
            f"{st.session_state.uploader_key}"
        ),
        help=(
            "PDF / TXT / Markdown / Word / Excel / "
            "PowerPoint / CSV / HTML / JSON に対応しています。"
        ),
    )


    # ========================================================
    # Register
    # ========================================================

    if uploaded_files:

        if st.button(
            "📥 登録する",
            type="primary",
            use_container_width=True,
        ):

            registered = []
            unchanged = []


            with st.status(
                "資料を処理しています...",
                expanded=True,
            ) as status_box:


                progress_bar = st.progress(
                    0,
                    text="処理を開始しています...",
                )


                phase_text = st.empty()

                detail_text = st.empty()


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

                        "document": (
                            5,
                            20,
                            "② 文書解析"
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
                        name,
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


                    phase_text.markdown(
                        f"**{name}**"
                    )


                    detail_text.caption(
                        message
                    )


                try:

                    for uploaded_file in uploaded_files:

                        result = register_document(
                            filename=(
                                uploaded_file.name
                            ),
                            file_bytes=(
                                uploaded_file.getvalue()
                            ),
                            mime_type=(
                                uploaded_file.type
                                or "application/octet-stream"
                            ),
                            document_type=(
                                document_type
                            ),
                            status=(
                                status
                            ),
                            valid_from=(
                                valid_from
                            ),
                            valid_to=(
                                valid_to
                            ),
                            progress_callback=(
                                update_progress
                            ),
                        )


                        if (
                            result["status"]
                            == "unchanged"
                        ):

                            unchanged.append(
                                result
                            )

                        else:

                            registered.append(
                                result
                            )


                    progress_bar.progress(
                        100,
                        text="100% - 登録完了",
                    )


                    status_box.update(
                        label=(
                            "登録処理が完了しました。"
                        ),
                        state="complete",
                        expanded=False,
                    )


                except Exception as e:

                    status_box.update(
                        label=(
                            "登録処理に失敗しました。"
                        ),
                        state="error",
                        expanded=True,
                    )


                    st.error(
                        str(e)
                    )

                    st.stop()


            st.session_state.uploader_key += 1


            if registered:

                registered_text = ", ".join(
                    (
                        f"{item['filename']} "
                        f"v{item['version']}"
                    )
                    for item
                    in registered
                )


                st.session_state.upload_success = (
                    f"登録しました: {registered_text}"
                )


            if unchanged:

                unchanged_text = ", ".join(
                    item["filename"]
                    for item
                    in unchanged
                )


                st.session_state.upload_info = (
                    "内容・管理情報に変更がないため、"
                    "Versionは追加していません: "
                    f"{unchanged_text}"
                )


            st.rerun()


# ============================================================
# Latest Documents Tab
# ============================================================

with tab_documents:

    st.markdown(
        """
<div class="section-card">
<div class="section-title">最新資料</div>
<div class="section-subtitle">
現在の最新版と、AIが検索対象にできる状態かを確認できます。
</div>
</div>
""",
        unsafe_allow_html=True,
    )


    latest_documents = get_documents(
        include_history=False
    )


    today = date.today()


    if not latest_documents:

        st.info(
            "資料が登録されていません。"
        )


    for document in latest_documents:


        # ----------------------------------------------------
        # Freshness
        # ----------------------------------------------------

        if document[
            "status"
        ] != "published":

            freshness = (
                "⚪ 下書き"
            )


        elif (
            document[
                "valid_from"
            ]
            and document[
                "valid_from"
            ] > today
        ):

            freshness = (
                "🔵 公開待ち"
            )


        elif (
            document[
                "valid_to"
            ]
            and document[
                "valid_to"
            ] < today
        ):

            freshness = (
                "🔴 期限切れ"
            )


        elif (
            document[
                "valid_to"
            ]
            and (
                document[
                    "valid_to"
                ]
                - today
            ).days <= 30
        ):

            freshness = (
                "🟡 更新確認推奨"
            )


        else:

            freshness = (
                "🟢 有効"
            )


        with st.container(
            border=True
        ):

            col1, col2, col3 = st.columns(
                [
                    5,
                    2,
                    1,
                ],
                vertical_alignment="center",
            )


            with col1:

                st.markdown(
                    (
                        f"### 📄 "
                        f"{document['filename']}"
                    )
                )


                st.caption(
                    (
                        f"Version {document['version']}"
                        f" / "
                        f"{document['document_type']}"
                        f" / "
                        f"{document['chunk_count']} Chunk"
                    )
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
                        f"サイズ: {size_mb:.2f} MB"
                    )
                )


            with col2:

                st.markdown(
                    f"**{freshness}**"
                )


                st.caption(
                    (
                        "公開状態: "
                        f"{document['status']}"
                    )
                )


                if document[
                    "valid_from"
                ]:

                    st.caption(
                        (
                            "開始: "
                            f"{document['valid_from']}"
                        )
                    )


                if document[
                    "valid_to"
                ]:

                    st.caption(
                        (
                            "終了: "
                            f"{document['valid_to']}"
                        )
                    )


            with col3:

                if st.button(
                    "🗑️",
                    key=(
                        "latest_delete_"
                        f"{document['id']}"
                    ),
                    help=(
                        f"{document['filename']} "
                        "を削除"
                    ),
                    use_container_width=True,
                ):

                    st.session_state.pending_delete = (
                        document["id"]
                    )

                    st.rerun()


# ============================================================
# History Tab
# ============================================================

with tab_history:

    st.markdown(
        """
<div class="section-card">
<div class="section-title">Version履歴</div>
<div class="section-subtitle">
最新版ではない旧Versionを確認できます。
</div>
</div>
""",
        unsafe_allow_html=True,
    )


    all_documents = get_documents(
        include_history=True
    )


    history = [
        document
        for document
        in all_documents
        if not document[
            "is_latest"
        ]
    ]


    if not history:

        st.info(
            "旧Versionはありません。"
        )


    # ========================================================
    # Filename単位
    # ========================================================

    filenames = sorted(
        set(
            document[
                "filename"
            ]
            for document
            in history
        )
    )


    for filename in filenames:

        with st.expander(
            f"📄 {filename}"
        ):

            versions = [
                document
                for document
                in history
                if document[
                    "filename"
                ]
                == filename
            ]


            versions = sorted(
                versions,
                key=lambda item: (
                    item[
                        "version"
                    ]
                ),
                reverse=True,
            )


            for document in versions:

                with st.container(
                    border=True
                ):

                    col1, col2, col3 = st.columns(
                        [
                            4,
                            3,
                            1,
                        ],
                        vertical_alignment="center",
                    )


                    with col1:

                        st.markdown(
                            (
                                f"**Version "
                                f"{document['version']}**"
                            )
                        )


                        st.caption(
                            (
                                f"{document['document_type']}"
                                f" / "
                                f"{document['chunk_count']} Chunk"
                            )
                        )


                    with col2:

                        st.caption(
                            (
                                "公開状態: "
                                f"{document['status']}"
                            )
                        )


                        st.caption(
                            (
                                "登録日時: "
                                f"{document['created_at']}"
                            )
                        )


                        if document[
                            "valid_from"
                        ]:

                            st.caption(
                                (
                                    "開始: "
                                    f"{document['valid_from']}"
                                )
                            )


                        if document[
                            "valid_to"
                        ]:

                            st.caption(
                                (
                                    "終了: "
                                    f"{document['valid_to']}"
                                )
                            )


                    with col3:

                        if st.button(
                            "🗑️",
                            key=(
                                "history_delete_"
                                f"{document['id']}"
                            ),
                            help=(
                                f"{filename} "
                                f"v{document['version']} "
                                "を削除"
                            ),
                            use_container_width=True,
                        ):

                            st.session_state.pending_delete = (
                                document[
                                    "id"
                                ]
                            )

                            st.rerun()