import os
import shlex
import subprocess
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# 環境変数
# ============================================================

load_dotenv()


LIPSYNC_ENABLED = (
    os.getenv(
        "LIPSYNC_ENABLED",
        "false",
    )
    .lower()
    == "true"
)


LIPSYNC_COMMAND = (
    os.getenv(
        "LIPSYNC_COMMAND",
        "",
    )
    .strip()
)


# ============================================================
# LipSync呼び出し
# ============================================================

def start_lipsync(
    audio_path: Path,
    text: str = "",
):

    # ========================================================
    # LipSync無効
    # ========================================================

    if not LIPSYNC_ENABLED:

        return None


    # ========================================================
    # コマンド未設定
    # ========================================================

    if not LIPSYNC_COMMAND:

        raise RuntimeError(
            "LIPSYNC_ENABLED=true ですが、"
            "LIPSYNC_COMMAND が設定されていません。"
        )


    audio_path = (
        audio_path.resolve()
    )


    # ========================================================
    # プレースホルダー置換
    #
    # {audio}
    # {text}
    #
    # を.envで使用可能
    # ========================================================

    command = (
        LIPSYNC_COMMAND
        .replace(
            "{audio}",
            str(audio_path),
        )
        .replace(
            "{text}",
            text,
        )
    )


    # ========================================================
    # Windows
    #
    # PowerShell / exe / python等を実行可能
    # ========================================================

    process = subprocess.Popen(
        command,
        shell=True,
    )


    return process