from io import BytesIO
from pathlib import Path
import re

from docx import Document
from docx.document import Document as _Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from fastapi import UploadFile
from pypdf import PdfReader


PDF_TYPE = "application/pdf"

DOCX_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)

TEXT_TYPES = {
    "text/plain",
    "text/markdown",
}


async def extract_document(
    file: UploadFile,
) -> list[dict]:
    content = await file.read()

    filename = file.filename or ""
    extension = Path(filename).suffix.lower()

    if (
        file.content_type == PDF_TYPE
        or extension == ".pdf"
    ):
        return _extract_pdf(content)

    if (
        file.content_type == DOCX_TYPE
        or extension == ".docx"
    ):
        return _extract_docx(content)

    if (
        file.content_type in TEXT_TYPES
        or extension in {
            ".txt",
            ".md",
        }
    ):
        return _extract_text(content)

    raise ValueError(
        "対応していないファイル形式です。"
        f" filename={filename},"
        f" content_type={file.content_type}"
    )


def _extract_pdf(
    content: bytes,
) -> list[dict]:
    reader = PdfReader(
        BytesIO(content)
    )

    parts = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text()

        if not text:
            continue

        text = text.strip()

        if not text:
            continue

        parts.append(
            {
                "text": text,
                "page_number": page_number,
                "section_title": None,
            }
        )

    return parts


def _extract_docx(
    content: bytes,
) -> list[dict]:
    document = Document(
        BytesIO(content)
    )

    parts = []

    current_section = None
    current_texts = []

    def flush_section():
        nonlocal current_texts

        if not current_texts:
            return

        text = "\n".join(
            current_texts
        ).strip()

        if not text:
            current_texts = []
            return

        parts.append(
            {
                "text": text,
                "page_number": None,
                "section_title": current_section,
            }
        )

        current_texts = []

    for block in _iter_block_items(
        document
    ):
        if isinstance(
            block,
            Paragraph,
        ):
            text = _normalize_line(
                block.text
            )

            if not text:
                continue

            if _is_heading_paragraph(
                block
            ):
                flush_section()

                current_section = text

                continue

            current_texts.append(
                text
            )

        elif isinstance(
            block,
            Table,
        ):
            table_text = (
                _extract_table_text(
                    block
                )
            )

            if not table_text:
                continue

            current_texts.append(
                table_text
            )

    flush_section()

    return parts


def _iter_block_items(
    document: _Document,
):
    """
    DOCX内の段落と表を、
    文書上の出現順に返す。
    """

    parent_element = (
        document.element.body
    )

    for child in (
        parent_element.iterchildren()
    ):
        if child.tag.endswith(
            "}p"
        ):
            yield Paragraph(
                child,
                document,
            )

        elif child.tag.endswith(
            "}tbl"
        ):
            yield Table(
                child,
                document,
            )


def _extract_table_text(
    table: Table,
) -> str:
    """
    表をテキスト化する。

    同じセルが結合などにより
    重複して取得される場合もあるため、
    行単位で重複を抑える。
    """

    rows = []

    for row in table.rows:
        values = []

        previous_value = None

        for cell in row.cells:
            value = _normalize_line(
                cell.text
            )

            if not value:
                continue

            if value == previous_value:
                continue

            values.append(
                value
            )

            previous_value = value

        if not values:
            continue

        row_text = " | ".join(
            values
        )

        rows.append(
            row_text
        )

    return "\n".join(
        rows
    ).strip()


def _is_heading_paragraph(
    paragraph: Paragraph,
) -> bool:
    """
    Word標準Headingだけでなく、
    見た目や文章パターンからも
    見出し候補を判定する。
    """

    text = _normalize_line(
        paragraph.text
    )

    if not text:
        return False

    # -----------------------------------------
    # 1. Word標準のHeadingスタイル
    # -----------------------------------------

    style_name = ""

    if paragraph.style:
        style_name = (
            paragraph.style.name
            or ""
        )

    normalized_style = (
        style_name
        .strip()
        .lower()
    )

    heading_style_keywords = [
        "heading",
        "見出し",
        "title",
        "subtitle",
    ]

    if any(
        keyword
        in normalized_style
        for keyword
        in heading_style_keywords
    ):
        return True

    # -----------------------------------------
    # 2. 長すぎる文章は見出し扱いしない
    # -----------------------------------------

    if len(text) > 120:
        return False

    # -----------------------------------------
    # 3. 文末が文章っぽい場合は除外
    # -----------------------------------------

    sentence_endings = (
        "。",
        "！",
        "？",
        ".",
        "?",
        "!",
    )

    if text.endswith(
        sentence_endings
    ):
        return False

    # -----------------------------------------
    # 4. 章番号パターン
    # -----------------------------------------

    heading_patterns = [
        r"^\d+\s+.+$",
        r"^\d+\.\s*.+$",
        r"^\d+\.\d+\s*.+$",
        r"^\d+\.\d+\.\d+\s*.+$",
        r"^\d+\)\s*.+$",
        r"^\(\d+\)\s*.+$",
        r"^[A-Z]\.\s+.+$",
        r"^[A-Z]\d*\s+.+$",
        r"^第\d+[章節項]\s*.+$",
        r"^[０-９]+[．.]\s*.+$",
    ]

    for pattern in heading_patterns:
        if re.match(
            pattern,
            text,
        ):
            return True

    # -----------------------------------------
    # 5. 太字主体の短い段落
    # -----------------------------------------

    if len(text) <= 80:
        visible_runs = [
            run
            for run in paragraph.runs
            if run.text.strip()
        ]

        if visible_runs:
            bold_count = sum(
                1
                for run in visible_runs
                if run.bold
            )

            if (
                bold_count
                == len(visible_runs)
            ):
                return True

    # -----------------------------------------
    # 6. フォントサイズが大きい
    # -----------------------------------------

    font_sizes = []

    for run in paragraph.runs:
        if not run.text.strip():
            continue

        if (
            run.font
            and run.font.size
        ):
            font_sizes.append(
                run.font.size.pt
            )

    if font_sizes:
        average_size = (
            sum(font_sizes)
            / len(font_sizes)
        )

        if (
            average_size >= 14
            and len(text) <= 100
        ):
            return True

    return False


def _extract_text(
    content: bytes,
) -> list[dict]:
    try:
        text = content.decode(
            "utf-8"
        )

    except UnicodeDecodeError:
        text = content.decode(
            "cp932"
        )

    text = text.strip()

    if not text:
        return []

    return [
        {
            "text": text,
            "page_number": None,
            "section_title": None,
        }
    ]


def _normalize_line(
    text: str,
) -> str:
    """
    DOCXから取得した文字列の
    改行や空白を整理する。
    """

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    lines = []

    for line in text.split(
        "\n"
    ):
        line = re.sub(
            r"[ \t]+",
            " ",
            line,
        ).strip()

        if line:
            lines.append(
                line
            )

    return "\n".join(
        lines
    ).strip()