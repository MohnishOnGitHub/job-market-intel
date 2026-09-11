from __future__ import annotations

import pytest

from app.core.exceptions import FileTooLargeError, ResumeParseError, UnsupportedFileTypeError
from app.services.resume_parser import extract_text, parse_resume, validate_resume_file


def make_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 24 Tf 50 700 Td ({escaped}) Tj ET"
    content_bytes = content.encode("latin-1", "replace")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        ),
        (
            b"4 0 obj << /Length "
            + str(len(content_bytes)).encode()
            + b" >> stream\n"
            + content_bytes
            + b"\nendstream endobj\n"
        ),
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    header = b"%PDF-1.4\n"
    body = b"".join(objects)
    offsets = []
    cursor = len(header)
    for obj in objects:
        offsets.append(cursor)
        cursor += len(obj)
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    xref.extend(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    trailer = (
        b"".join(xref)
        + b"trailer << /Size 6 /Root 1 0 R >>\n"
        + f"startxref\n{len(header) + len(body)}\n".encode()
        + b"%%EOF\n"
    )
    return header + body + trailer


def test_rejects_empty_file():
    with pytest.raises(ResumeParseError):
        validate_resume_file(b"")


def test_rejects_non_pdf():
    with pytest.raises(UnsupportedFileTypeError):
        validate_resume_file(b"not a pdf", filename="resume.txt", content_type="text/plain")


def test_rejects_oversized_file(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    from app.core.config import clear_settings_cache

    clear_settings_cache()
    too_big = b"%PDF" + (b"a" * (1024 * 1024 + 10))
    with pytest.raises(FileTooLargeError):
        validate_resume_file(too_big, filename="resume.pdf")


def test_parse_resume_extracts_lowercased_text():
    pdf = make_pdf("Python SQL FastAPI")
    text = parse_resume(pdf, filename="resume.pdf", content_type="application/pdf")
    assert "python" in text
    assert "sql" in text
    assert "fastapi" in text
    assert text == text.lower()


def test_extract_text_does_not_write_temp_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    extract_text(make_pdf("docker kubernetes"))
    assert not (tmp_path / "temp.pdf").exists()
    assert list(tmp_path.glob("*.pdf")) == []


def test_empty_pdf_text_raises():
    with pytest.raises(ResumeParseError):
        extract_text(make_pdf(""))
