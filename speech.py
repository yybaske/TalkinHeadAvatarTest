from pathlib import Path
from uuid import uuid4

from openai import OpenAI


# ============================================================
# 設定
# ============================================================

TTS_MODEL = "gpt-4o-mini-tts"

TTS_VOICE = "alloy"

AUDIO_DIR = Path("./audio")

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
) -> Path:

    text = text.strip()

    if not text:

        raise ValueError(
            "TTS対象のテキストが空です。"
        )


    # ========================================================
    # ファイル名
    # ========================================================

    filename = (
        f"speech_{uuid4().hex}.wav"
    )

    output_path = (
        AUDIO_DIR
        / filename
    )


    # ========================================================
    # 音声生成
    # ========================================================

    with (
        client.audio.speech
        .with_streaming_response
        .create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=text,
            response_format="wav",
            instructions=(
                "自然で落ち着いた日本語で、"
                "聞き取りやすく話してください。"
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
    keep_latest: int = 20,
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


    for file_path in files[
        keep_latest:
    ]:

        try:

            file_path.unlink()

        except Exception:

            pass