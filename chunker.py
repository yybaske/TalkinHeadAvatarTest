import re


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


def split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    テキストをRAG検索用のチャンクに分割する。

    - 段落や文の境界をできるだけ維持する
    - chunk_sizeを大きく超えないようにする
    - 前チャンクの末尾を次チャンクに一部含める
    """

    text = _normalize_text(text)

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        target_end = min(start + chunk_size, len(text))

        if target_end < len(text):
            end = _find_split_position(
                text=text,
                start=start,
                target_end=target_end,
            )
        else:
            end = len(text)

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        next_start = max(end - chunk_overlap, start + 1)

        # overlapの途中から文章が始まるのを少しだけ避ける
        adjusted_start = _find_next_start(text, next_start, end)

        start = adjusted_start

    return chunks


def _normalize_text(text: str) -> str:
    """
    不要な空白を整理する。
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # スペースだけの行を除去
    text = re.sub(r"[ \t]+\n", "\n", text)

    # 3つ以上の改行を2つに
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _find_split_position(
    text: str,
    start: int,
    target_end: int,
) -> int:
    """
    target_endより少し前から、
    自然な文章境界を探す。
    """

    search_start = max(
        start,
        target_end - 300,
    )

    candidates = [
        "\n\n",
        "\n",
        "。",
        "！",
        "？",
        ". ",
    ]

    best_position = -1

    for separator in candidates:
        position = text.rfind(
            separator,
            search_start,
            target_end,
        )

        if position != -1:
            position += len(separator)

            if position > best_position:
                best_position = position

    if best_position > start:
        return best_position

    return target_end


def _find_next_start(
    text: str,
    next_start: int,
    previous_end: int,
) -> int:
    """
    overlap開始位置を可能な範囲で文章境界に寄せる。
    """

    search_end = min(
        next_start + 100,
        previous_end,
    )

    separators = [
        "\n\n",
        "\n",
        "。",
        "！",
        "？",
    ]

    for separator in separators:
        position = text.find(
            separator,
            next_start,
            search_end,
        )

        if position != -1:
            return position + len(separator)

    return next_start