"""Exception types for the ingestion pipeline. Every failure is explicit; nothing falls back silently."""


class IngestionError(Exception):
    """Base class for all ingestion failures (bad config, unreadable source, failed validation)."""


class MissingDependencyError(IngestionError):
    """An optional library needed for the requested source format is not installed."""

    def __init__(self, package: str, needed_for: str, pip_name: str | None = None):
        self.package = package
        pip_name = pip_name or package
        super().__init__(
            f"{needed_for} requires the Python package '{package}', which is not installed. "
            f"Install it with: uv pip install {pip_name}  (or: pip install {pip_name})"
        )


class NoTextLayerError(IngestionError):
    """A PDF has no extractable text layer (scanned/image-only). OCR is not implemented."""


class ConfigError(IngestionError):
    """The ingestion YAML is missing a field or contains an unsupported value."""


class ValidationFailed(IngestionError):
    """The built corpus failed validation. The manifest records the errors."""
