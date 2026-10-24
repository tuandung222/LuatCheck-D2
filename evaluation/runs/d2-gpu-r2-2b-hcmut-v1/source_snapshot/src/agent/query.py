"""Query construction helpers of the controller. Domain-agnostic: words only, no vocabulary."""
from typing import List

_EDGE = ".,;:!?\"'()[]{}«»“”‘’…-–—"


def _key(word: str) -> str:
    return word.strip(_EDGE).lower()


def anchor_query(question: str, model_query: str) -> str:
    """`retrieval.first_search_anchor: question_plus_query`: the user's question followed by the words of the model's query that
    the question does not already contain (compared case-insensitively, ignoring edge punctuation; each added word once, without
    its edge punctuation).

    The question keeps its own words and order; only the model's extra words are appended. If the model adds nothing new,
    the result is the (whitespace-normalised) question."""
    base = " ".join(str(question).split())
    seen = {key for key in (_key(w) for w in base.split()) if key}
    extra: List[str] = []
    for word in str(model_query).split():
        key = _key(word)
        if key and key not in seen:
            seen.add(key)
            extra.append(word.strip(_EDGE))
    return base if not extra else base + " " + " ".join(extra)
