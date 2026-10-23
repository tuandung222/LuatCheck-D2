"""Shared small types: search hits and the metadata filter language."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, NamedTuple, Optional, Sequence

Metadata = Dict[str, Any]
# A filter is {field: value} or {field: [v1, v2, ...]}: all fields must match (AND); a list means any-of (OR).
# Values are compared with strict equality (no type coercion). A missing field never matches.
MetadataFilter = Mapping[str, Any]


class Hit(NamedTuple):
    """One search result: `(id, score, metadata)`. Higher score is always better."""

    id: str
    score: float
    metadata: Metadata


def validate_filter(flt: Optional[MetadataFilter]) -> Optional[Dict[str, List[Any]]]:
    """Normalise a filter to {field: [allowed values]} or None. Raises ValueError on bad input."""
    if not flt:
        return None
    out: Dict[str, List[Any]] = {}
    for field, wanted in flt.items():
        if not isinstance(field, str) or not field:
            raise ValueError(f"filter field names must be non-empty strings, got {field!r}")
        values = list(wanted) if isinstance(wanted, (list, tuple, set, frozenset)) else [wanted]
        if not values:
            raise ValueError(f"filter on {field!r} has an empty value list")
        for v in values:
            if not isinstance(v, (str, int, float, bool)):
                raise ValueError(f"filter values must be str/int/float/bool, got {type(v).__name__} for {field!r}")
        out[field] = values
    return out


def _equal(actual: Any, wanted: Any) -> bool:
    # bool is an int subclass in Python; keep True != 1 so backends with typed payloads agree.
    if isinstance(actual, bool) or isinstance(wanted, bool):
        return isinstance(actual, bool) and isinstance(wanted, bool) and actual == wanted
    if isinstance(actual, (int, float)) and isinstance(wanted, (int, float)):
        return actual == wanted
    return isinstance(actual, str) and isinstance(wanted, str) and actual == wanted


def matches_filter(metadata: Mapping[str, Any], flt: Optional[Dict[str, List[Any]]]) -> bool:
    """True if `metadata` satisfies a filter already normalised by `validate_filter`."""
    if not flt:
        return True
    return all(field in metadata and any(_equal(metadata[field], v) for v in values)
               for field, values in flt.items())


def is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def rank_by_score(pairs: Iterable[tuple[str, float]]) -> List[tuple[str, float]]:
    """Sort (id, score) by score descending, ties by id ascending (deterministic)."""
    return sorted(pairs, key=lambda p: (-p[1], p[0]))
