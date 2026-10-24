"""Domain-general document ingestion: PDF/DOCX/HTML/Markdown/text -> normalised text -> structure-aware chunks
-> validated corpus JSON + manifest. See docs/design/ingestion.md."""

__version__ = "0.1.0"

from .errors import (ConfigError, IngestionError, MissingDependencyError, NoTextLayerError,  # noqa: E402
                     ValidationFailed)
from .schema import Chunk, LEVELS  # noqa: E402

__all__ = ["Chunk", "LEVELS", "IngestionError", "ConfigError", "MissingDependencyError", "NoTextLayerError",
           "ValidationFailed", "build", "write_outputs", "register_ruleset", "__version__"]


def build(*args, **kwargs):
    from .pipeline import build as _build
    return _build(*args, **kwargs)


def write_outputs(*args, **kwargs):
    from .pipeline import write_outputs as _write
    return _write(*args, **kwargs)


def register_ruleset(cls):
    from .rulesets import register_ruleset as _register
    return _register(cls)
