"""Verification mode vocabulary (`verifier.mode`).

Light module with no heavy imports so that the config layer, the pipeline and the agent share one definition.

Canonical modes:

* ``off``                  no verification (the answer is accepted as the model wrote it)
* ``lexical_grounding``    L1: citation existence, retrieval provenance, lexical overlap, exact quantities
* ``semantic_entailment``  L1 followed by L2 (native-model entailment; needs ``verifier.l2_use_slm: true``)

Every other accepted value is an alias of one of these.
"""
from enum import Enum
from typing import Any, Dict, Optional

OFF = "off"
LEXICAL_GROUNDING = "lexical_grounding"
SEMANTIC_ENTAILMENT = "semantic_entailment"

MODE_ALIASES: Dict[str, str] = {
    "off": OFF,
    "lexical_grounding": LEXICAL_GROUNDING, "lexical": LEXICAL_GROUNDING, "grounding": LEXICAL_GROUNDING,
    "l1": LEXICAL_GROUNDING, "l1_only": LEXICAL_GROUNDING, "l1_on": LEXICAL_GROUNDING,
    "semantic_entailment": SEMANTIC_ENTAILMENT, "semantic": SEMANTIC_ENTAILMENT, "full": SEMANTIC_ENTAILMENT,
    "l1_l2": SEMANTIC_ENTAILMENT, "l1_l2_on": SEMANTIC_ENTAILMENT,
}
VALID_MODES = frozenset(MODE_ALIASES)


class VerificationMode(str, Enum):
    OFF = "off"
    LEXICAL_GROUNDING = "lexical_grounding"
    SEMANTIC_ENTAILMENT = "semantic_entailment"
    FULL = "full"


def canonical_mode(mode: Any) -> str:
    """Canonical mode of a configured value (enum, alias, mixed case or padded). Unknown values are returned
    lower-cased and stripped, so callers can still report them; use `is_valid_mode` to check."""
    raw = mode.value if hasattr(mode, "value") else str(mode)
    text = raw.strip().lower()
    return MODE_ALIASES.get(text, text)


def is_valid_mode(mode: Any) -> bool:
    return canonical_mode(mode) in VALID_MODES


def resolve_mode(configured: str, override: Optional[str] = None, enable_verification: Optional[bool] = None) -> str:
    """Mode for one agent: an explicit `override` beats the configured value, and the legacy boolean
    `enable_verification` forces ``off`` (False) or turns an ``off`` mode into L1 (True).

    The returned value is the raw (possibly aliased) string; the agent keeps it as given.
    Raises ValueError for a mode outside `VALID_MODES`.
    """
    chosen = override if override is not None else configured
    if enable_verification is False:
        mode = OFF
    elif enable_verification is True and chosen == OFF:
        mode = LEXICAL_GROUNDING
    else:
        mode = chosen
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid verification mode {mode!r}; expected one of {sorted(VALID_MODES)}")
    return mode
