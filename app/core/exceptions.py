from __future__ import annotations


class AppError(Exception):
    """Domain error mapped to an HTTP response by the API layer."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnsupportedFileTypeError(AppError):
    def __init__(self, message: str = "Unsupported file type. Upload a PDF résumé.") -> None:
        super().__init__(message, 400)


class FileTooLargeError(AppError):
    def __init__(self, message: str = "File is too large.") -> None:
        super().__init__(message, 413)


class ResumeParseError(AppError):
    def __init__(self, message: str = "Could not read text from the uploaded PDF.") -> None:
        super().__init__(message, 400)


class DatabaseUnavailableError(AppError):
    def __init__(self, message: str = "Database is not configured or unavailable.") -> None:
        super().__init__(message, 503)


class JobValidationError(Exception):
    """A single job record is invalid and should be skipped."""


class JobSourceError(AppError):
    def __init__(self, message: str = "Job source request failed.") -> None:
        super().__init__(message, 502)


class IngestionError(AppError):
    def __init__(self, message: str = "Ingestion failed.") -> None:
        super().__init__(message, 500)
