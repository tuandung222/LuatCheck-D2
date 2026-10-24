"""Length-safe chunking: long records are split into overlapping chunks, never truncated.

Token mode (providers with a tokenizer, e.g. the local model) windows over real tokenizer
offsets so every chunk is guaranteed to fit the model; character mode (HTTP providers without
a tokenizer) windows over whitespace-delimited words with a character budget.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .errors import ConfigError

Span = Tuple[int, int]
OffsetsFn = Callable[[str], List[Span]]

_SENTENCE_END = ".;:!?\n"


@dataclass(frozen=True)
class ChunkingConfig:
    max_tokens: int = 512          # token budget per chunk (token mode), including special tokens
    overlap_tokens: int = 64
    max_chars: int = 1500          # character budget per chunk (character mode)
    overlap_chars: int = 200
    contextual_title: bool = True  # prefix chunks after the first with the record title when it fits
    special_tokens: int = 2        # reserved for [CLS]/[SEP]-style tokens
    title_token_cap: int = 48      # titles longer than this are not prefixed (token mode)
    title_char_cap: int = 200      # titles longer than this are not prefixed (char mode)

    def validate(self) -> None:
        if self.max_tokens <= self.special_tokens + 8 or self.overlap_tokens < 0 or self.overlap_tokens >= self.max_tokens // 2:
            raise ConfigError("chunking: need max_tokens > 10 and 0 <= overlap_tokens < max_tokens/2")
        if self.max_chars < 100 or self.overlap_chars < 0 or self.overlap_chars >= self.max_chars // 2:
            raise ConfigError("chunking: need max_chars >= 100 and 0 <= overlap_chars < max_chars/2")

    @classmethod
    def from_dict(cls, d: Optional[Dict]) -> "ChunkingConfig":
        d = dict(d or {})
        unknown = set(d) - set(cls.__dataclass_fields__)
        if unknown:
            raise ConfigError(f"chunking: unknown keys {sorted(unknown)}")
        cfg = cls(**d)
        cfg.validate()
        return cfg

    def as_dict(self) -> Dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class Chunk:
    doc_id: str
    index: int
    count: int
    start: int            # character span in the record content
    end: int
    text: str             # content[start:end]
    embed_text: str       # what is actually embedded (text, optionally prefixed with the title)

    @property
    def chunk_id(self) -> str:
        return self.doc_id if self.count == 1 else f"{self.doc_id}#c{self.index}"


def _word_spans(text: str) -> List[Span]:
    return [m.span() for m in re.finditer(r"\S+", text)]


def _window(text: str, spans: Sequence[Span], weights: Sequence[int], budget: int, overlap: int) -> List[Span]:
    """Greedy overlapping windows over units; returns character spans covering all units."""
    n = len(spans)
    out: List[Span] = []
    i = 0
    while i < n:
        j, w = i, 0
        while j < n and w + weights[j] <= budget:
            w += weights[j]
            j += 1
        if j == i:  # one unit alone exceeds the budget: emit it as its own chunk (reported by the provider)
            j = i + 1
        if j < n:  # prefer to end on a sentence/line boundary within the last quarter of the window
            lo = i + max(1, (3 * (j - i)) // 4)
            for k in range(j, lo - 1, -1):
                end_char = spans[k - 1][1]
                if text[end_char - 1] in _SENTENCE_END or "\n" in text[end_char:spans[k][0]]:
                    j = k
                    break
        out.append((spans[i][0], spans[j - 1][1]))
        if j >= n:
            break
        k, ow = j, 0
        while k > i + 1 and ow + weights[k - 1] <= overlap:
            ow += weights[k - 1]
            k -= 1
        i = max(k, i + 1)
    return out


def chunk_record(
    record: Dict,
    cfg: ChunkingConfig,
    offsets_fn: Optional[OffsetsFn] = None,
    title_tokens: Optional[int] = None,
) -> List[Chunk]:
    """Split one record's content. `offsets_fn(text)` returns token character offsets (token mode)."""
    doc_id, content = record["doc_id"], record["content"]
    title = (record.get("title") or "").strip()

    use_title = False
    if cfg.contextual_title and title:
        if offsets_fn is not None:
            ttok = title_tokens if title_tokens is not None else len(offsets_fn(title))
            use_title = ttok <= cfg.title_token_cap
            reserve = cfg.special_tokens + (ttok + 1 if use_title else 0)
        else:
            use_title = len(title) <= cfg.title_char_cap
            reserve = len(title) + 1 if use_title else 0
    else:
        reserve = cfg.special_tokens if offsets_fn is not None else 0

    if offsets_fn is not None:
        spans = offsets_fn(content)
        weights = [1] * len(spans)
        budget, overlap = cfg.max_tokens - reserve, cfg.overlap_tokens
    else:
        spans = _word_spans(content)
        weights = [(e - s) + 1 for s, e in spans]
        budget, overlap = cfg.max_chars - reserve, cfg.overlap_chars
    if not spans:
        raise ConfigError(f"{doc_id}: content has no tokens")

    # first chunk: whole record if it fits the budget (without the title prefix, which is only for later chunks)
    first_budget = (cfg.max_tokens - cfg.special_tokens) if offsets_fn is not None else cfg.max_chars
    if sum(weights) <= first_budget:
        char_spans = [(0, len(content))]
    else:
        char_spans = _window(content, spans, weights, budget, overlap)
        # a first chunk without a title prefix could use the full budget, but equal budgets keep chunks uniform
        char_spans[0] = (0, char_spans[0][1])
        char_spans[-1] = (char_spans[-1][0], len(content))

    chunks: List[Chunk] = []
    count = len(char_spans)
    for idx, (s, e) in enumerate(char_spans):
        text = content[s:e]
        embed_text = text
        if idx > 0 and use_title and not text.lstrip().startswith(title):
            embed_text = f"{title}\n{text}"
        chunks.append(Chunk(doc_id, idx, count, s, e, text, embed_text))
    return chunks
