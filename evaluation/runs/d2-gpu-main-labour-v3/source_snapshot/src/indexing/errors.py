"""Exception hierarchy for the indexing layer.

Every failure in this package is raised as one of these errors. Nothing here is
ever turned into an empty result, a zero vector or a fallback to another backend
(see AGENTS.md: a backend failure is an execution error).
"""


class IndexingError(Exception):
    """Base class for all indexing errors."""


class ConfigError(IndexingError):
    """Invalid or incomplete index/backend configuration."""


class BackendUnavailableError(IndexingError):
    """An optional dependency (or its native extension) is not installed or cannot load."""


class BackendError(IndexingError):
    """A vector store / keyword index operation failed."""


class EmbeddingError(IndexingError):
    """An embedding provider failed (model load, HTTP error, malformed response, bad values)."""


class TextTooLongError(EmbeddingError):
    """A text exceeds the embedding model's maximum length; it is never truncated silently."""


class MemoryLimitError(IndexingError):
    """The process exceeded the configured resident-memory limit."""


class StaleIndexError(IndexingError):
    """The persisted index no longer matches the corpus or the embedding model."""


class ManifestError(IndexingError):
    """Missing or malformed manifest."""
