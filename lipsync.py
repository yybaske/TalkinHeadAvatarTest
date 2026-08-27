import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv


# ============================================================
# Environment
# ============================================================

load_dotenv()


# ============================================================
# Base Directory
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


# ============================================================
# Video Directory
# ============================================================

VIDEO_DIR = (
    BASE_DIR
    / "video"
)


VIDEO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Settings
# ============================================================

LIPSYNC_ENABLED = (
    os.getenv(
        "LIPSYNC_ENABLED",
        "false",
    )
    .strip()
    .lower()
    == "true"
)


LIPSYNC_TIMEOUT = int(
    os.getenv(
        "LIPSYNC_TIMEOUT",
        "300",
    )
)


# ============================================================
# Wav2Lip Paths
# ============================================================

WAV2LIP_DIR = (
    BASE_DIR
    / "Wav2Lip"
).resolve()


WAV2LIP_INFERENCE = (
    WAV2LIP_DIR
    / "inference.py"
).resolve()


checkpoint_setting = os.getenv(
    "WAV2LIP_CHECKPOINT",
    "Wav2Lip/checkpoints/Wav2Lip-SD-GAN.pt",
)


face_setting = os.getenv(
    "WAV2LIP_FACE",
    "assets/avatar_idle.mp4",
)


WAV2LIP_CHECKPOINT = (
    BASE_DIR
    / checkpoint_setting
).resolve()


WAV2LIP_FACE = (
    BASE_DIR
    / face_setting
).resolve()


# ============================================================
# Status
# ============================================================

def get_lipsync_status():

    return {

        "enabled": (
            LIPSYNC_ENABLED
        ),

        "python": (
            sys.executable
        ),

        "wav2lip_dir": str(
            WAV2LIP_DIR
        ),

        "inference": str(
            WAV2LIP_INFERENCE
        ),

        "inference_exists": (
            WAV2LIP_INFERENCE.exists()
        ),

        "checkpoint": str(
            WAV2LIP_CHECKPOINT
        ),

        "checkpoint_exists": (
            WAV2LIP_CHECKPOINT.exists()
        ),

        "face": str(
            WAV2LIP_FACE
        ),

        "face_exists": (
            WAV2LIP_FACE.exists()
        ),

        "video_dir": str(
            VIDEO_DIR
        ),

    }


# ============================================================
# Wav2Lip事前チェック
# ============================================================

def validate_wav2lip():

    errors = []


    # --------------------------------------------------------
    # inference.py
    # --------------------------------------------------------

    if not WAV2LIP_INFERENCE.exists():

        errors.append(
            (
                "Wav2Lipのinference.pyが"
                "見つかりません。\n"
                f"{WAV2LIP_INFERENCE}"
            )
        )


    # --------------------------------------------------------
    # Checkpoint
    # --------------------------------------------------------

    if not WAV2LIP_CHECKPOINT.exists():

        errors.append(
            (
                "Wav2LipのCheckpointが"
                "見つかりません。\n"
                f"{WAV2LIP_CHECKPOINT}"
            )
        )


    # --------------------------------------------------------
    # Avatar
    # --------------------------------------------------------

    if not WAV2LIP_FACE.exists():

        errors.append(
            (
                "アバター元動画が"
                "見つかりません。\n"
                f"{WAV2LIP_FACE}"
            )
        )


    # --------------------------------------------------------
    # Error
    # --------------------------------------------------------

    if errors:

        raise RuntimeError(
            "\n\n".join(
                errors
            )
        )


# ============================================================
# LipSync
# ============================================================

def start_lipsync(
    audio_path: Path,
    text: str = "",
):

    # ========================================================
    # Enabled
    # ========================================================

    if not LIPSYNC_ENABLED:

        raise RuntimeError(
            (
                "LipSyncが無効です。\n"
                ".env の "
                "LIPSYNC_ENABLED=true "
                "を確認してください。"
            )
        )


    # ========================================================
    # Wav2Lip Check
    # ========================================================

    validate_wav2lip()


    # ========================================================
    # Audio
    # ========================================================

    audio_path = (
        Path(
            audio_path
        )
        .resolve()
    )


    if not audio_path.exists():

        raise FileNotFoundError(
            (
                "音声ファイルが"
                "見つかりません。\n"
                f"{audio_path}"
            )
        )


    if (
        audio_path
        .stat()
        .st_size
        == 0
    ):

        raise RuntimeError(
            (
                "音声ファイルが0バイトです。\n"
                f"{audio_path}"
            )
        )


    # ========================================================
    # Output
    # ========================================================

    output_path = (
        VIDEO_DIR
        / (
            "avatar_"
            f"{uuid4().hex}"
            ".mp4"
        )
    ).resolve()


    # ========================================================
    # Command
    #
    # shell=True を使わない
    #
    # 日本語パス対策として
    # subprocessへ引数配列を直接渡す
    # ========================================================

    command = [

        sys.executable,

        str(
            WAV2LIP_INFERENCE
        ),

        "--checkpoint_path",

        str(
            WAV2LIP_CHECKPOINT
        ),

        "--face",

        str(
            WAV2LIP_FACE
        ),

        "--audio",

        str(
            audio_path
        ),

        "--outfile",

        str(
            output_path
        ),

    ]


    # ========================================================
    # Debug用コマンド表示
    # ========================================================

    command_display = " ".join(
        f'"{value}"'
        if " " in value
        else value
        for value in command
    )


    # ========================================================
    # Execute
    # ========================================================

    try:

        result = subprocess.run(

            command,

            shell=False,

            capture_output=True,

            text=True,

            encoding="utf-8",

            errors="replace",

            timeout=(
                LIPSYNC_TIMEOUT
            ),

            # ------------------------------------------------
            # Wav2Lipの内部相対パス対策
            # ------------------------------------------------

            cwd=str(
                WAV2LIP_DIR
            ),

        )


    except subprocess.TimeoutExpired as e:

        raise RuntimeError(
            (
                "Wav2Lip処理が"
                "タイムアウトしました。\n\n"
                f"Timeout: "
                f"{LIPSYNC_TIMEOUT}秒\n\n"
                f"Command:\n"
                f"{command_display}"
            )
        ) from e


    except Exception as e:

        raise RuntimeError(
            (
                "Wav2Lipを起動できませんでした。\n\n"
                f"Command:\n"
                f"{command_display}\n\n"
                f"Error:\n"
                f"{e}"
            )
        ) from e


    # ========================================================
    # stdout / stderr
    # ========================================================

    stdout = (
        result.stdout
        or ""
    ).strip()


    stderr = (
        result.stderr
        or ""
    ).strip()


    # ========================================================
    # Return Code
    # ========================================================

    if result.returncode != 0:

        raise RuntimeError(
            (
                "Wav2Lip処理が失敗しました。\n\n"

                f"終了コード: "
                f"{result.returncode}\n\n"

                f"Command:\n"
                f"{command_display}\n\n"

                f"STDOUT:\n"
                f"{stdout or '(なし)'}\n\n"

                f"STDERR:\n"
                f"{stderr or '(なし)'}"
            )
        )


    # ========================================================
    # Output Check
    # ========================================================

    if not output_path.exists():

        raise RuntimeError(
            (
                "Wav2Lipは正常終了しましたが、"
                "動画が生成されていません。\n\n"

                f"想定出力先:\n"
                f"{output_path}\n\n"

                f"Command:\n"
                f"{command_display}\n\n"

                f"STDOUT:\n"
                f"{stdout or '(なし)'}\n\n"

                f"STDERR:\n"
                f"{stderr or '(なし)'}"
            )
        )


    # ========================================================
    # Size
    # ========================================================

    file_size = (
        output_path
        .stat()
        .st_size
    )


    if file_size <= 1024:

        raise RuntimeError(
            (
                "動画は生成されましたが、"
                "ファイルサイズが小さすぎます。\n\n"

                f"Video:\n"
                f"{output_path}\n\n"

                f"Size: "
                f"{file_size} bytes"
            )
        )


    # ========================================================
    # Success
    # ========================================================

    return {

        "video_path": (
            output_path
        ),

        "command": (
            command_display
        ),

        "return_code": (
            result.returncode
        ),

        "stdout": (
            stdout
        ),

        "stderr": (
            stderr
        ),

        "file_size": (
            file_size
        ),

    }


# ============================================================
# Cleanup
# ============================================================

def cleanup_video_files(
    keep_latest: int = 10,
):

    files = sorted(

        VIDEO_DIR.glob(
            "avatar_*.mp4"
        ),

        key=lambda path: (
            path
            .stat()
            .st_mtime
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