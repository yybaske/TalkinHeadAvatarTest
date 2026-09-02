import re


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


def split_document(
    parts: list[dict],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """
    ページ番号や見出し情報を維持したまま、
    文書をチャンク化する。
    """

    result = []

    chunk_index = 0

    for part in parts:
        text = part.get(
            "text",
            "",
        )

        if not text.strip():
            continue

        chunks = split_text(
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk in chunks:
            result.append(
                {
                    "chunk_index": chunk_index,
                    "content": chunk,
                    "page_number": part.get(
                        "page_number"
                    ),
                    "section_title": part.get(
                        "section_title"
                    ),
                }
            )

            chunk_index += 1

    return result


def split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    text = _normalize_text(text)

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        target_end = min(
            start + chunk_size,
            len(text),
        )

        if target_end < len(text):
            end = _find_split_position(
                text=text,
                start=start,
                target_end=target_end,
            )
        else:
            end = len(text)

        chunk = text[
            start:end
        ].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        next_start = max(
            end - chunk_overlap,
            start + 1,
        )

        start = _find_next_start(
            text=text,
            next_start=next_start,
            previous_end=end,
        )

    return chunks


def _normalize_text(
    text: str,
) -> str:
    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    text = re.sub(
        r"[ \t]+\n",
        "\n",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def _find_split_position(
    text: str,
    start: int,
    target_end: int,
) -> int:
    search_start = max(
        start,
        target_end - 300,
    )

    separators = [
        "\n\n",
        "\n",
        "。",
        "！",
        "？",
        ". ",
    ]

    best_position = -1

    for separator in separators:
        position = text.rfind(
            separator,
            search_start,
            target_end,
        )

        if position == -1:
            continue

        position += len(
            separator
        )

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
            return (
                position
                + len(separator)
            )

    return next_start