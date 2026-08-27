from pathlib import Path

import streamlit as st

from db import (
    init_database,
    check_database,
)

from rag import (
    get_documents,
    search,
    generate_answer_stream,
    generate_speech_text,
    get_location_label,
)

from speech import (
    text_to_speech,
    cleanup_audio_files,
)

from lipsync import (
    start_lipsync,
    cleanup_video_files,
    LIPSYNC_ENABLED,
)


# ============================================================
# Page
# ============================================================

st.set_page_config(
    page_title="Sales AI",
    page_icon="💬",
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
    max-width: 1500px;
    padding-top: 1.4rem;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-bottom: 3rem;
}


/* ==========================================================
   Header
========================================================== */

.sales-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    padding: 18px 24px;

    border: 1px solid rgba(128, 128, 128, 0.20);
    border-radius: 16px;

    margin-bottom: 20px;
}


.sales-header-left {
    min-width: 0;
}


.sales-title {
    font-size: 28px;
    font-weight: 700;
}


.sales-subtitle {
    margin-top: 5px;
    font-size: 14px;
    opacity: 0.68;
}


.sales-online {
    display: inline-flex;
    align-items: center;
    gap: 7px;

    padding: 7px 12px;

    border-radius: 999px;

    background: rgba(40, 170, 100, 0.10);

    font-size: 13px;
}


.online-dot {
    width: 9px;
    height: 9px;

    border-radius: 50%;

    background: #39b972;
}


/* ==========================================================
   Avatar
========================================================== */

.avatar-header {
    padding: 14px 18px;

    border: 1px solid rgba(128,128,128,0.18);
    border-radius: 14px;

    margin-bottom: 12px;
}


.avatar-title {
    font-size: 18px;
    font-weight: 650;
}


.avatar-subtitle {
    font-size: 13px;
    opacity: 0.65;
    margin-top: 3px;
}


/* ==========================================================
   Idle Avatar
========================================================== */

.idle-avatar-card {
    min-height: 440px;

    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;

    border: 1px solid rgba(128,128,128,0.18);
    border-radius: 20px;

    padding: 30px;

    text-align: center;

    overflow: hidden;
}


.idle-avatar {
    width: 190px;
    height: 190px;

    display: flex;
    justify-content: center;
    align-items: center;

    border-radius: 50%;

    background: rgba(128,128,128,0.08);

    font-size: 88px;

    animation:
        avatarFloat 3.2s ease-in-out infinite,
        avatarBreath 4s ease-in-out infinite;
}


.idle-avatar-name {
    margin-top: 24px;

    font-size: 21px;
    font-weight: 650;
}


.idle-avatar-status {
    margin-top: 8px;

    font-size: 14px;
    opacity: 0.7;
}


.idle-avatar-dot {
    display: inline-block;

    width: 8px;
    height: 8px;

    margin-right: 7px;

    border-radius: 50%;

    background: #39b972;

    animation:
        statusPulse 1.7s ease-in-out infinite;
}


/* ==========================================================
   Animations
========================================================== */

@keyframes avatarFloat {

    0% {
        transform: translateY(0);
    }

    50% {
        transform: translateY(-10px);
    }

    100% {
        transform: translateY(0);
    }

}


@keyframes avatarBreath {

    0% {
        scale: 1;
    }

    50% {
        scale: 1.025;
    }

    100% {
        scale: 1;
    }

}


@keyframes statusPulse {

    0% {
        opacity: 0.4;
    }

    50% {
        opacity: 1;
    }

    100% {
        opacity: 0.4;
    }

}


@media (
    prefers-reduced-motion: reduce
) {

    .idle-avatar,
    .idle-avatar-dot {
        animation: none;
    }

}


/* ==========================================================
   Chat
========================================================== */

.chat-header {
    padding: 14px 18px;

    border: 1px solid rgba(128,128,128,0.18);
    border-radius: 14px;

    margin-bottom: 12px;
}


.chat-title {
    font-size: 18px;
    font-weight: 650;
}


.chat-subtitle {
    margin-top: 3px;

    font-size: 13px;
    opacity: 0.65;
}


/* ==========================================================
   Streamlit Chat
========================================================== */

[data-testid="stChatMessage"] {
    border-radius: 14px;
}


/* ==========================================================
   Video
========================================================== */

[data-testid="stVideo"] {
    border-radius: 18px;
    overflow: hidden;

    border: 1px solid rgba(128,128,128,0.18);
}


/* ==========================================================
   Mobile
========================================================== */

@media (
    max-width: 900px
) {

    .sales-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 12px;
    }

    .idle-avatar-card {
        min-height: 300px;
    }

    .idle-avatar {
        width: 130px;
        height: 130px;

        font-size: 60px;
    }

}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# Session State
# ============================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


if "speech_enabled" not in st.session_state:

    st.session_state.speech_enabled = True


if "avatar_video_path" not in st.session_state:

    st.session_state.avatar_video_path = None


if "avatar_state" not in st.session_state:

    st.session_state.avatar_state = "idle"


# ============================================================
# DB
# ============================================================

try:

    init_database()

    db_ok = (
        check_database()
    )

except Exception:

    db_ok = False


if not db_ok:

    st.error(
        "現在サービスを利用できません。"
        "しばらくしてからもう一度お試しください。"
    )

    st.stop()


# ============================================================
# Documents
# ============================================================

documents = get_documents(
    include_history=False
)


if not documents:

    st.warning(
        "現在ご案内可能な情報がありません。"
    )

    st.stop()


# ============================================================
# Initial Chat
# ============================================================

if not st.session_state.messages:

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": (
                "こんにちは。"
                "製品やサービスについて、"
                "気になることがあればお気軽にご質問ください。"
            ),
        }
    )


# ============================================================
# Header
# ============================================================

st.markdown(
    """
<div class="sales-header">
<div class="sales-header-left">
<div class="sales-title">Sales AI</div>
<div class="sales-subtitle">
製品やサービスについて、最新の情報をもとにご案内します。
</div>
</div>
<div class="sales-online">
<span class="online-dot"></span>
Online
</div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# Layout
# ============================================================

avatar_col, chat_col = st.columns(
    [
        4,
        6,
    ],
    gap="large",
)


# ============================================================
# Avatar Column
# ============================================================

with avatar_col:

    st.markdown(
        """
<div class="avatar-header">
<div class="avatar-title">AI Assistant</div>
<div class="avatar-subtitle">
音声とアバターでご案内します。
</div>
</div>
""",
        unsafe_allow_html=True,
    )


    # ========================================================
    # Avatar Placeholder
    # ========================================================

    avatar_placeholder = (
        st.empty()
    )


    # ========================================================
    # Stored LipSync Video
    # ========================================================

    stored_video_path = (
        st.session_state
        .avatar_video_path
    )


    if stored_video_path:

        stored_video = Path(
            stored_video_path
        )


        if stored_video.exists():

            with avatar_placeholder.container():

                st.video(
                    str(
                        stored_video
                    ),
                    autoplay=True,
                )

                st.caption(
                    "🟢 AI Assistant"
                )


        else:

            st.session_state.avatar_video_path = None

            stored_video_path = None


    # ========================================================
    # Idle Animation
    # ========================================================

    if not stored_video_path:

        avatar_placeholder.markdown(
            """
<div class="idle-avatar-card">
<div class="idle-avatar">🤖</div>
<div class="idle-avatar-name">
AI Assistant
</div>
<div class="idle-avatar-status">
<span class="idle-avatar-dot"></span>
ご質問をお待ちしています
</div>
</div>
""",
            unsafe_allow_html=True,
        )


    # ========================================================
    # Audio Toggle
    # ========================================================

    st.session_state.speech_enabled = (
        st.toggle(
            "🔊 音声・アバターで回答する",
            value=(
                st.session_state
                .speech_enabled
            ),
        )
    )


    if st.session_state.speech_enabled:

        if LIPSYNC_ENABLED:

            st.caption(
                "音声：ON / アバター：ON"
            )

        else:

            st.caption(
                "音声：ON / アバター：待機モード"
            )

    else:

        st.caption(
            "音声：OFF"
        )


# ============================================================
# Chat Column
# ============================================================

with chat_col:

    st.markdown(
        """
<div class="chat-header">
<div class="chat-title">💬 ご相談・お問い合わせ</div>
<div class="chat-subtitle">
商品・サービス・導入方法など、お気軽にご質問ください。
</div>
</div>
""",
        unsafe_allow_html=True,
    )


    # ========================================================
    # History
    # ========================================================

    for message in (
        st.session_state.messages
    ):

        with st.chat_message(
            message[
                "role"
            ]
        ):

            st.markdown(
                message[
                    "content"
                ]
            )


    # ========================================================
    # Chat Input
    # ========================================================

    question = st.chat_input(
        "メッセージを入力してください"
    )


    # ========================================================
    # Question
    # ========================================================

    if question:

        # ----------------------------------------------------
        # User
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Assistant
        # ----------------------------------------------------

        with st.chat_message(
            "assistant"
        ):


            # =================================================
            # Progress
            # =================================================

            with st.container(
                border=True
            ):

                search_status = (
                    st.empty()
                )

                answer_status = (
                    st.empty()
                )

                speech_status = (
                    st.empty()
                )

                avatar_status = (
                    st.empty()
                )


            # =================================================
            # Search
            # =================================================

            search_status.markdown(
                "🔎 **最新情報を確認しています...**"
            )


            try:

                search_results = (
                    search(
                        question
                    )
                )

            except Exception:

                search_status.markdown(
                    "❌ **情報を確認できませんでした**"
                )

                st.error(
                    "申し訳ありません。"
                    "現在情報を確認できません。"
                )

                st.stop()


            search_status.markdown(
                "✅ **情報を確認しました**"
            )


            # =================================================
            # LLM
            # =================================================

            answer_status.markdown(
                "💭 **回答を考えています...**"
            )


            answer_area = (
                st.empty()
            )


            full_answer = ""


            try:

                for delta in (
                    generate_answer_stream(
                        question,
                        search_results,
                    )
                ):

                    full_answer += (
                        delta
                    )


                    answer_area.markdown(
                        full_answer
                        + " ▌"
                    )


            except Exception:

                answer_status.markdown(
                    "❌ **回答を生成できませんでした**"
                )

                st.error(
                    "申し訳ありません。"
                    "回答の生成中にエラーが発生しました。"
                )

                st.stop()


            answer_area.markdown(
                full_answer
            )


            answer_status.markdown(
                "✅ **回答しました**"
            )


            # =================================================
            # TTS
            # =================================================

            audio_path = None
            speech_text = ""


            if (
                st.session_state.speech_enabled
                and full_answer.strip()
            ):

                try:

                    speech_status.markdown(
                        "🗣️ **話す内容を準備しています...**"
                    )


                    speech_text = (
                        generate_speech_text(
                            full_answer
                        )
                    )


                    speech_status.markdown(
                        "🔊 **音声を生成しています...**"
                    )


                    audio_path = (
                        text_to_speech(
                            speech_text
                        )
                    )


                    speech_status.markdown(
                        "✅ **音声を生成しました**"
                    )


                except Exception:

                    speech_status.markdown(
                        "⚠️ **音声を生成できませんでした**"
                    )


            # =================================================
            # LipSync
            # =================================================

            generated_video = None


            if (
                audio_path is not None
                and LIPSYNC_ENABLED
            ):

                try:

                    avatar_status.markdown(
                        "👄 **アバターが話す準備をしています...**"
                    )


                    generated_video = (
                        start_lipsync(
                            audio_path,
                            speech_text,
                        )
                    )


                    if generated_video:

                        st.session_state.avatar_video_path = (
                            str(
                                generated_video
                            )
                        )


                        avatar_status.markdown(
                            "✅ **アバター動画を生成しました**"
                        )


                        # ------------------------------------
                        # 左カラムを書き換える
                        # ------------------------------------

                        with avatar_placeholder.container():

                            st.video(
                                str(
                                    generated_video
                                ),
                                autoplay=True,
                            )

                            st.caption(
                                "🟢 AI Assistantがお話ししています"
                            )


                except Exception as e:

                    avatar_status.markdown(
                        "⚠️ **アバターを生成できませんでした**"
                    )

                    st.caption(
                        str(e)
                    )


            # =================================================
            # TTS-only fallback
            # =================================================

            if (
                audio_path is not None
                and generated_video is None
            ):

                st.audio(
                    str(
                        audio_path
                    ),
                    format="audio/wav",
                    autoplay=True,
                )


            # =================================================
            # Sources
            # =================================================

            if search_results:

                with st.expander(
                    "回答の根拠を見る"
                ):

                    for result in (
                        search_results
                    ):

                        location = (
                            get_location_label(
                                result
                            )
                        )


                        st.markdown(
                            (
                                f"**{result['source']}**  \n"
                                f"{location}"
                            )
                        )


                        if (
                            "version"
                            in result
                        ):

                            st.caption(
                                (
                                    "Version "
                                    f"{result['version']}"
                                )
                            )


                        st.divider()


        # ====================================================
        # History
        # ====================================================

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": full_answer,
            }
        )


# ============================================================
# Cleanup
# ============================================================

cleanup_audio_files(
    keep_latest=10
)


cleanup_video_files(
    keep_latest=10
)