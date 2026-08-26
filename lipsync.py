import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# Environment
# ============================================================

load_dotenv()


# ============================================================
# 設定
# ============================================================

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
# LipSync
# ============================================================

def start_lipsync(
    audio_path: Path,
    text: str = "",
):

    if not LIPSYNC_ENABLED:

        return None


    if not LIPSYNC_COMMAND:

        raise RuntimeError(
            "LIPSYNC_ENABLED=true ですが、"
            "LIPSYNC_COMMAND が設定されていません。"
        )


    audio_path = (
        audio_path.resolve()
    )


    command = (
        LIPSYNC_COMMAND
        .replace(
            "{audio}",
            str(
                audio_path
            ),
        )
        .replace(
            "{text}",
            text,
        )
    )


    return subprocess.Popen(
        command,
        shell=True,
    )