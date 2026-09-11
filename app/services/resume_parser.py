from __future__ import annotations

from io import BytesIO

from PyPDF2 import PdfReader

from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError, ResumeParseError, UnsupportedFileTypeError

_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
}


def validate_resume_file(
    file_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> None:
    settings = get_settings()
    if not file_bytes:
        raise ResumeParseError("The uploaded file is empty.")

    if len(file_bytes) > settings.max_upload_bytes:
        raise FileTooLargeError(
            f"File exceeds the {settings.max_upload_mb} MB upload limit."
        )

    name = (filename or "").lower()
    ctype = (content_type or "").split(";")[0].strip().lower()
    looks_like_pdf = file_bytes.startswith(b"%PDF")
    named_pdf = name.endswith(".pdf")
    typed_pdf = ctype in _PDF_CONTENT_TYPES

    if not (looks_like_pdf or named_pdf or typed_pdf):
        raise UnsupportedFileTypeError()


def extract_text(file_bytes: bytes) -> str:
    """Extract and lowercase PDF text in memory. Does not write to disk."""
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise ResumeParseError("Could not read the uploaded PDF.") from exc

    if getattr(reader, "is_encrypted", False):
        raise ResumeParseError("Encrypted PDFs are not supported.")

    parts: list[str] = []
    try:
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)
    except Exception as exc:
        raise ResumeParseError("Could not extract text from the uploaded PDF.") from exc

    text = "".join(parts).strip()
    if not text:
        raise ResumeParseError(
            "No extractable text found. Use a text-based PDF, not a scanned image."
        )
    return text.lower()


def parse_resume(
    file_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> str:
    validate_resume_file(file_bytes, filename=filename, content_type=content_type)
    return extract_text(file_bytes)
