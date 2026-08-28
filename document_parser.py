from io import BytesIO

from fastapi import UploadFile
from pypdf import PdfReader


async def extract_text(file: UploadFile) -> str:
    content = await file.read()

    if file.content_type == "application/pdf":
        return _extract_pdf_text(content)

    if file.content_type in {
        "text/plain",
        "text/markdown",
    }:
        return _extract_text_file(content)

    raise ValueError(
        f"Unsupported file type: {file.content_type}"
    )


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))

    texts = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            texts.append(text)

    return "\n\n".join(texts)


def _extract_text_file(content: bytes) -> str:
    try:
        return content.decode("utf-8")

    except UnicodeDecodeError:
        return content.decode("cp932")