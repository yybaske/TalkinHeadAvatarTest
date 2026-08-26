from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# Environment
# ============================================================

load_dotenv()


# ============================================================
# 設定
# ============================================================

TTS_MODEL = "gpt-4o-mini-tts"

TTS_VOICE = "alloy"


BASE_DIR = Path(
    __file__
).resolve().parent


AUDIO_DIR = (
    BASE_DIR
    / "audio"
)


AUDIO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# OpenAI
# ============================================================

client = OpenAI()


# ============================================================
# TTS
# ============================================================

def text_to_speech(
    text: str,
):

    text = (
        text.strip()
    )


    if not text:

        raise ValueError(
            "TTS対象テキストが空です。"
        )


    filename = (
        f"speech_{uuid4().hex}.wav"
    )


    output_path = (
        AUDIO_DIR
        / filename
    )


    with (
        client.audio.speech
        .with_streaming_response
        .create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=text,
            response_format="wav",
            instructions=(
                "自然な日本語の会話として話してください。"
                "営業担当者にアドバイスするような、"
                "落ち着いて聞き取りやすい口調にしてください。"
            ),
        )
    ) as response:

        response.stream_to_file(
            output_path
        )


    return output_path


# ============================================================
# 古い音声削除
# ============================================================

def cleanup_audio_files(
    keep_latest=10,
):

    files = sorted(
        AUDIO_DIR.glob(
            "speech_*.wav"
        ),
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )


    for file_path in (
        files[
            keep_latest:
        ]
    ):

        try:

            file_path.unlink()

        except Exception:

            pass