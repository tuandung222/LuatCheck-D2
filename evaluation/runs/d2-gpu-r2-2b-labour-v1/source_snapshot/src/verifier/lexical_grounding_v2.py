"""
L1 v2: lexical grounding with fair quote matching, claim-local quantities and actionable repair feedback.

Same contract as `lexical_grounding.LexicalGroundingVerifier` (v1, kept byte-for-byte for the frozen runs), selected
with ``verifier.l1_version: v2``. Still rule-based, deterministic and domain-agnostic: unit vocabulary, stopwords, ID
convention and feedback wording come from the domain profile. Every score here is a *lexical proxy*; a pass is not a
statement that the answer is correct.

What changes with respect to v1 (all choices fixed a priori; the support threshold is the only calibrated number,
see `evaluation/runs/l1-replay-2026-10-24/NOTE.md`):

1. Exact quote. Both sides are folded (Unicode NFC, case, whitespace, typographic quotes/dashes) and the wrapper
   characters of the quote (quotation marks, brackets, edge punctuation) are stripped. A quote may contain elisions
   (``...``, ``…``, ``[...]``, ``(...)``): it passes when every non-trivial segment (>= 12 characters or >= 3 words)
   occurs verbatim in the cited record, in order. Numbers must match exactly: a segment that starts or ends in a
   digit may not match inside a longer number, and every number of a skipped trivial segment must occur in the
   record. A paraphrase still fails. The quote must come from the cited record.
2. Source units. Cited records are cut into sentences (soft line wraps joined, list items and ``;`` start a new
   sentence, units longer than `MAX_UNIT_CHARS` are chunked). A *window* is one unit, two adjacent units of the same
   record, or a list item with the sentence that introduces its list: a clause with its lead-in or continuation.
   Only a single unit or a multi-unit window of at most `MAX_WINDOW_CHARS` can anchor a quantity.
3. Claim support. An answer sentence is scored against its best single window: the fraction of its content tokens
   (stopwords and the quantity itself removed) found in that window. It is supported when the fraction is >=
   `support_threshold`.
4. Claim-local quantities. A number+unit of an answer sentence must occur in a window that matches the words around
   it (8 on each side) as well as any window does (same number of those content tokens as the best window). A wrong
   number that is printed elsewhere in the same record therefore fails; the 3,5 / 3.5 normalisation and the
   newline-unit handling are kept.
5. Feedback names the failing check per quote/sentence and shows the closest source span verbatim (clipped), so the
   controller can copy the text or correct the number.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from src.agent.state import Citation, GroundingVerificationResult
from src.domains import DomainProfile
from src.verifier.lexical_grounding import LexicalGroundingVerifier, _quantity_key, split_sentences

# --- fixed (a priori) parameters -------------------------------------------------------------------------------
MIN_SEGMENT_CHARS = 12      # an elision segment shorter than this AND shorter than MIN_SEGMENT_WORDS is "trivial":
MIN_SEGMENT_WORDS = 3       # its order is not checked (it is too short to discriminate), only its numbers
MAX_UNIT_CHARS = 400        # about twice a typical sentence; a longer unit (table, run-on paragraph) is chunked
CHUNK_CHARS = 250
MAX_WINDOW_CHARS = 300      # only a unit or a multi-unit window up to this length can anchor a quantity (long windows win on word counts alone)
QUANTITY_CONTEXT_TOKENS = 8   # words on each side of a number+unit that describe the clause it governs
SPAN_CHARS = 170            # clip length of the source span shown in repair feedback
CLAIM_CHARS = 80            # clip length of a quoted answer sentence in repair feedback
MAX_FEEDBACK_ITEMS = 2      # token budget of a 2B controller: at most this many findings per repair message
NEAR_VERBATIM = 0.4         # a quote is "a copy with a local error" when this share of it is a verbatim prefix
DEFAULT_SUPPORT_THRESHOLD = 0.50   # set by the a-priori rule on the bll2019 development set (evaluation/probes/l1_replay.py dev)

_FOLD_MAP = str.maketrans({
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"', "\u00ab": '"', "\u00bb": '"', "\u2033": '"',
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u2032": "'", "`": "'",
    "\u2013": "-", "\u2014": "-", "\u2011": "-", "\u2212": "-",
    "\u00a0": " ", "\u2009": " ", "\u202f": " ",
    "\u200b": None, "\u200c": None, "\u200d": None, "\ufeff": None,       # zero-width characters
})
_CLOSERS, _OPENERS = ",;:.!?)]}", "([{"
_MARKER = r"(?:\d{1,2}[.)]|[^\W\d_]\))\s+"            # list numbering: "2. ", "a) "
_LEADING_MARKER = re.compile(r"^" + _MARKER + r"(?=\w)")
_SENTENCE_GAP = re.compile(r"(?<=[.;:!?]) ")
_WRAP_CHARS = " \t\r\n\"'()[]{}<>*_.,;:!?-"
_ELLIPSIS = re.compile(r"\[\s*(?:\.{2,}|…)\s*\]|\(\s*(?:\.{2,}|…)\s*\)|\.{3,}|…")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_WORD = re.compile(r"\w+")
_ENUMERATOR = re.compile(r"^\s*(?:\d+[.)]|\d+\.\d+(?:\.\d+)*|[^\W\d_]\)|[-•*–])\s")
_SOURCE_SPLIT = re.compile(r"(?:(?<=[?!;])\s*|(?<!\b\d[.])(?<!\b\d\d[.])(?<!\b\d\d\d[.])(?<=[.])\s+|\n+)")
_LINE_END = tuple('.;:!?"\'\u201d')


def fold_with_map(text: str) -> Tuple[str, List[int]]:
    """`fold` plus, for every character of the folded text, its index in the NFC-normalised input."""
    nfc = unicodedata.normalize("NFC", str(text))
    chars: List[str] = []
    index: List[int] = []
    pending_space = False
    for i, ch in enumerate(nfc):
        mapped = ch.translate(_FOLD_MAP)
        if not mapped:
            continue
        if mapped.isspace():
            pending_space = bool(chars)
            continue
        if pending_space:
            # typographic spacing is not content: no space before a closing mark or after an opening one
            if mapped[0] not in _CLOSERS and chars[-1] not in _OPENERS:
                chars.append(" ")
                index.append(i)
            pending_space = False
        for piece in mapped.lower():
            chars.append(piece)
            index.append(i)
    folded = "".join(chars)
    return folded, index


def fold(text: str) -> str:
    """Unicode NFC, typographic quotes/dashes unified, lower case, whitespace collapsed."""
    return fold_with_map(text)[0]


def _strip_wrap(text: str) -> str:
    return text.strip(_WRAP_CHARS)


def _words(text: str) -> List[str]:
    return _WORD.findall(text.lower())


# --- quote matching --------------------------------------------------------------------------------------------

def _find_bounded(record: str, segment: str, start: int = 0) -> int:
    """Index of `segment` in `record` at or after `start`, or -1. A segment edge on a digit must not sit inside a
    longer number (so '5 tháng' is not found in '3,5 tháng' or '15 tháng')."""
    position = record.find(segment, start)
    while position >= 0:
        end = position + len(segment)
        before = record[position - 1] if position > 0 else ""
        before2 = record[position - 2] if position > 1 else ""
        after = record[end] if end < len(record) else ""
        after2 = record[end + 1] if end + 1 < len(record) else ""
        left_bad = segment[0].isdigit() and (before.isdigit() or (before in ".," and before2.isdigit()))
        right_bad = segment[-1].isdigit() and (after.isdigit() or (after in ".," and after2.isdigit()))
        if not (left_bad or right_bad):
            return position
        position = record.find(segment, position + 1)
    return -1


def _is_trivial(segment: str) -> bool:
    return len(segment) < MIN_SEGMENT_CHARS and len(segment.split()) < MIN_SEGMENT_WORDS


def _marker_tolerant(segment: str) -> "re.Pattern[str]":
    """Pattern of `segment` that also accepts list numbering ("2. ", "a) ") the source has after a sentence end and the
    quote omitted. Only an omission is tolerated: every character of the quote must still be present."""
    pieces = [re.escape(piece) for piece in _SENTENCE_GAP.split(segment)]
    pattern = (r" (?:" + _MARKER + r")?").join(pieces)
    if segment[0].isdigit():
        pattern = r"(?<!\d)(?<!\d[.,])" + pattern
    if segment[-1].isdigit():
        pattern = pattern + r"(?!\d)(?![.,]\d)"
    return re.compile(pattern)


def _find_segment(record: str, segment: str, start: int = 0) -> Tuple[int, int]:
    """(begin, end) of the first match of `segment` in `record` at or after `start`, or (-1, -1): verbatim first, then
    tolerating omitted list numbering."""
    position = _find_bounded(record, segment, start)
    if position >= 0:
        return position, position + len(segment)
    match = _marker_tolerant(segment).search(record, start)
    return (match.start(), match.end()) if match else (-1, -1)


@dataclass
class QuoteCheck:
    ok: bool
    failing: Optional[str] = None     # the (folded) quote segment that was not found
    kind: Optional[str] = None        # "segment" | "number"


def check_quote(quote: str, record_folded: str) -> QuoteCheck:
    """Exact-quote check of `quote` against an already folded record text (see the module docstring)."""
    folded = _strip_wrap(fold(quote))
    if not folded:
        return QuoteCheck(True)
    if _find_segment(record_folded, folded)[0] >= 0:
        return QuoteCheck(True)          # whole quote verbatim (also when the source itself contains '[...]')
    if not _ELLIPSIS.search(folded):
        return QuoteCheck(False, folded, "segment")
    segments = [s for s in (_strip_wrap(_LEADING_MARKER.sub("", _strip_wrap(part))) for part in _ELLIPSIS.split(folded)) if s]
    if not segments:
        return QuoteCheck(True)
    required = [s for s in segments if not _is_trivial(s)] or segments
    position = 0
    for segment in required:
        begin, end = _find_segment(record_folded, segment, position)
        if begin < 0:
            return QuoteCheck(False, segment, "segment")
        position = end
    record_numbers = set(_NUMBER.findall(record_folded))
    for segment in segments:
        if segment in required:
            continue
        for number in _NUMBER.findall(segment):
            if number not in record_numbers:
                return QuoteCheck(False, segment, "number")
    return QuoteCheck(True)


# --- source units and windows ----------------------------------------------------------------------------------

def _join_soft_wraps(text: str) -> str:
    """Hard-wrapped PDF text: a newline is a boundary only after sentence-final punctuation or before a list marker."""
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n")]
    out: List[str] = []
    for line in lines:
        if not line:
            continue
        if out and not out[-1].endswith(_LINE_END) and not _ENUMERATOR.match(line + " "):
            out[-1] = out[-1] + " " + line
        else:
            out.append(line)
    return "\n".join(out)


def _chunk(unit: str) -> List[str]:
    if len(unit) <= MAX_UNIT_CHARS:
        return [unit]
    chunks, current = [], ""
    for word in unit.split(" "):
        if current and len(current) + 1 + len(word) > CHUNK_CHARS:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        chunks.append(current)
    return chunks


def source_units(text: str) -> List[str]:
    units: List[str] = []
    for sentence in _SOURCE_SPLIT.split(_join_soft_wraps(text)):
        sentence = sentence.strip()
        if sentence:
            units.extend(_chunk(sentence))
    return units


@dataclass(frozen=True)
class Window:
    record_id: str
    text: str
    tokens: FrozenSet[str]
    quantities: FrozenSet[str]
    anchor: bool = True       # may anchor a quantity: a single unit, or a multi-unit window of <= MAX_WINDOW_CHARS


def window_texts(units: List[str]) -> List[Tuple[str, ...]]:
    """Windows over source units: each unit alone, each pair of adjacent units, and each list item together with the
    sentence that introduces its list (the last non-item sentence containing ':'), so that an item far down a list is
    still read with its lead-in ("...trong một học kỳ chính như sau:" + "- Sinh viên ...: 09 tín chỉ")."""
    spans: List[Tuple[str, ...]] = [(u,) for u in units]
    spans += [(units[i], units[i + 1]) for i in range(len(units) - 1)]
    lead: Optional[int] = None
    for i, unit in enumerate(units):
        if _ENUMERATOR.match(unit + " "):
            if lead is not None and lead < i - 1:
                spans.append((units[lead], unit))
        else:
            lead = i if ":" in unit else None
    return spans


def _windows(record_id: str, text: str, quantity_pattern: str) -> List[Window]:
    windows = []
    for span in window_texts(source_units(text)):
        joined = " ".join(span)
        lowered = joined.lower()
        windows.append(Window(record_id, joined, frozenset(_WORD.findall(lowered)),
                              frozenset(_quantity_key(q) for q in re.findall(quantity_pattern, lowered)),
                              len(span) == 1 or len(joined) <= MAX_WINDOW_CHARS))
    return windows


def clip(text: str, query_tokens: FrozenSet[str], limit: int) -> str:
    """At most `limit` characters of `text`, verbatim, positioned where most `query_tokens` occur."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    words = text.split(" ")
    best, best_start = -1, 0
    for i in range(len(words)):
        size, hits, j = 0, 0, i
        while j < len(words) and size + len(words[j]) + 1 <= limit:
            size += len(words[j]) + 1
            hits += 1 if any(t in query_tokens for t in _WORD.findall(words[j].lower())) else 0
            j += 1
        if hits > best:
            best, best_start = hits, i
    out, size = [], 0
    for word in words[best_start:]:
        if size + len(word) + 1 > limit:
            break
        out.append(word)
        size += len(word) + 1
    return ("… " if best_start > 0 else "") + " ".join(out) + (" …" if best_start + len(out) < len(words) else "")


# --- report ----------------------------------------------------------------------------------------------------

@dataclass
class L1Finding:
    kind: str                         # see KINDS
    message: str                      # repair feedback line for this finding
    citation: Optional[str] = None
    sentence: Optional[str] = None
    quantity: Optional[str] = None
    span: Optional[str] = None        # closest source span shown to the model
    detail: Dict[str, Any] = field(default_factory=dict)


SENTENCE_SUPPORT_MODES = ("block", "warn")
KINDS = ("empty_answer", "missing_citation", "unknown_citation", "unretrieved_citation", "quote_mismatch",
         "claim_unsupported", "quantity_absent", "quantity_not_local")
_PRIORITY = {k: i for i, k in enumerate(KINDS)}


@dataclass
class L1Report:
    findings: List[L1Finding] = field(default_factory=list)        # blocking: any of them rejects the answer
    warnings: List[L1Finding] = field(default_factory=list)        # sentence-support failures in `warn` mode: recorded, not blocking
    sentences: List[Dict[str, Any]] = field(default_factory=list)   # per answer sentence: coverage, quantity status

    @property
    def passed(self) -> bool:
        return not self.findings

    @property
    def reasons(self) -> List[str]:
        return [f.kind for f in self.findings]


# --- verifier --------------------------------------------------------------------------------------------------

class LexicalGroundingVerifierV2(LexicalGroundingVerifier):
    """L1 v2. `overlap_threshold` (the v1 bag-of-words threshold) is accepted and ignored; use `support_threshold`."""

    version = "v2"

    def __init__(self, corpus: List[Dict[str, Any]], similarity_threshold: float = 0.65, overlap_threshold: float = 0.25,
                 profile: Optional[DomainProfile] = None, support_threshold: float = DEFAULT_SUPPORT_THRESHOLD,
                 sentence_support: str = "block"):
        super().__init__(corpus, similarity_threshold=similarity_threshold, overlap_threshold=overlap_threshold,
                         profile=profile)
        if not 0.0 <= support_threshold <= 1.0:
            raise ValueError(f"support_threshold must be in [0, 1], got {support_threshold!r}")
        if sentence_support not in SENTENCE_SUPPORT_MODES:
            raise ValueError(f"sentence_support must be one of {list(SENTENCE_SUPPORT_MODES)}, got {sentence_support!r}")
        self.support_threshold = float(support_threshold)
        # "block": an unsupported sentence rejects the answer. "warn": it is reported in L1Report.warnings / the result's
        # `warnings` and the answer is not rejected; quote and quantity failures still block.
        self.sentence_support = sentence_support
        self._folded: Dict[str, Tuple[str, List[int], str]] = {}
        self._windows: Dict[str, List[Window]] = {}

    # -- record access (cached; the corpus does not change) -----------------------------------------------------
    @staticmethod
    def _record_text(doc: Dict[str, Any]) -> str:
        title = doc.get("title") or ""
        content = doc.get("content") or doc.get("full_content") or ""
        return content if (not title or content.startswith(title)) else f"{title}\n{content}"

    def _fold_cache(self, norm_id: str) -> Tuple[str, List[int], str]:
        if norm_id not in self._folded:
            raw = unicodedata.normalize("NFC", self._record_text(self.valid_article_ids[norm_id]))
            folded, index = fold_with_map(raw)
            self._folded[norm_id] = (folded, index, raw)
        return self._folded[norm_id]

    def _folded_record(self, norm_id: str) -> str:
        return self._fold_cache(norm_id)[0]

    def _record_windows(self, norm_id: str) -> List[Window]:
        if norm_id not in self._windows:
            self._windows[norm_id] = _windows(norm_id, self._record_text(self.valid_article_ids[norm_id]),
                                              self.profile.quantity_pattern)
        return self._windows[norm_id]

    # -- public API ---------------------------------------------------------------------------------------------
    def verify(self, answer_text: str, citations: List[Citation],
               retrieved_article_ids: List[str]) -> GroundingVerificationResult:
        report = self.analyze(answer_text, citations, retrieved_article_ids)
        warnings = [self._warning_record(f) for f in report.warnings]
        if report.passed:
            return GroundingVerificationResult(is_valid=True, unsupported_claims=[], invalid_citations=[],
                                               repair_feedback=None, warnings=warnings)
        shown = sorted(report.findings, key=lambda f: _PRIORITY[f.kind])[:MAX_FEEDBACK_ITEMS]
        messages = self.profile.messages
        if report.findings[0].kind == "empty_answer":
            unsupported, invalid = [messages.l1_empty_answer_claim], []
        elif report.findings[0].kind == "missing_citation":
            unsupported, invalid = [answer_text.strip()], ["MISSING_CITATION"]
        else:
            unsupported = list(dict.fromkeys(f.sentence for f in report.findings if f.sentence))
            invalid = [f.message for f in report.findings
                       if f.kind in ("unknown_citation", "unretrieved_citation", "quote_mismatch")]
        rejected = self._reject(feedback="\n".join(f.message for f in shown), unsupported=unsupported, invalid=invalid)
        rejected.warnings = warnings
        return rejected

    @staticmethod
    def _warning_record(finding: L1Finding) -> Dict[str, Any]:
        return {"kind": finding.kind, "check": "sentence_support", "sentence": finding.sentence, "span": finding.span,
                **finding.detail}

    def analyze(self, answer_text: str, citations: List[Citation], retrieved_article_ids: List[str]) -> L1Report:
        """All findings of one draft (citation problems and unsupported sentences together)."""
        messages = self.profile.messages
        if not answer_text or not answer_text.strip():
            return L1Report([L1Finding("empty_answer", messages.l1_empty_answer_feedback)])
        if not citations:
            return L1Report([L1Finding("missing_citation", messages.l1_missing_citation_feedback)])
        findings, usable = self._citation_findings(citations, retrieved_article_ids)
        scored: List[Dict[str, Any]] = []
        warnings: List[L1Finding] = []
        if usable:
            ids = frozenset(t for c in citations for t in (c.article_id.lower(), self._normalize_id(c.article_id)))
            findings.extend(self._sentence_findings(answer_text, usable, scored, ids, warnings))
        return L1Report(findings, warnings, scored)

    # -- citations ---------------------------------------------------------------------------------------------
    def _citation_findings(self, citations: List[Citation], retrieved_article_ids: List[str]) -> Tuple[List[L1Finding], List[str]]:
        messages = self.profile.messages
        retrieved = {self._normalize_id(a) for a in retrieved_article_ids}
        findings: List[L1Finding] = []
        usable: List[str] = []
        for c in citations:
            norm = self._normalize_id(c.article_id)
            if norm not in self.valid_article_ids:
                findings.append(L1Finding("unknown_citation", messages.l1_unknown_citation.format(doc_id=c.article_id),
                                          citation=c.article_id))
                continue
            if norm not in retrieved:
                findings.append(L1Finding("unretrieved_citation", messages.unretrieved_citation.format(doc_id=c.article_id),
                                          citation=c.article_id))
            elif norm not in usable:
                usable.append(norm)
            if c.exact_quote:
                check = check_quote(c.exact_quote, self._folded_record(norm))
                if not check.ok:
                    findings.append(self._quote_finding(c, norm, check, retrieved))
        return findings, usable

    def _quote_finding(self, c: Citation, norm: str, check: QuoteCheck, retrieved: Iterable[str]) -> L1Finding:
        failing = check.failing or fold(c.exact_quote or "")
        query = frozenset(_words(failing))
        for other in dict.fromkeys(retrieved):          # the quote is real but cited under the wrong id?
            if other != norm and other in self.valid_article_ids and check_quote(c.exact_quote or "", self._folded_record(other)).ok:
                shown = self._display_id(other)
                return L1Finding("quote_mismatch", self.profile.messages.l1v2_quote_other_record.format(
                    doc_id=c.article_id, other_id=shown), citation=c.article_id,
                    detail={"segment": failing, "check": check.kind, "other_record": shown})
        span = self._divergence_span(norm, failing)
        if span is None:
            best = self._closest(query, self._record_windows(norm))
            span = clip(best.text, query, SPAN_CHARS) if best else ""
        message = self.profile.messages.l1v2_quote_mismatch.format(doc_id=c.article_id, span=span)
        return L1Finding("quote_mismatch", message, citation=c.article_id, span=span,
                         detail={"segment": failing, "check": check.kind})

    def _divergence_span(self, norm: str, failing: str) -> Optional[str]:
        """Source text from just before the point where the quote stops being verbatim, or None when even the first
        words of the quote are not in the record (then the closest window is shown instead)."""
        folded, index, raw = self._fold_cache(norm)
        words = failing.split(" ")
        low, high = 0, len(words) - 1
        while low < high:
            mid = (low + high + 1) // 2
            if _find_bounded(folded, " ".join(words[:mid])) >= 0:
                low = mid
            else:
                high = mid - 1
        prefix = " ".join(words[:low])
        if low == 0 or len(prefix) < max(MIN_SEGMENT_CHARS, NEAR_VERBATIM * len(failing)):
            return None            # a paraphrase, not a near-verbatim copy with a local error
        end = _find_bounded(folded, prefix) + len(prefix)
        start = max(0, end - 40)
        raw_start = index[start]
        raw_end = index[min(start + SPAN_CHARS + 80, len(index) - 1)]
        return ("… " if raw_start > 0 else "") + clip(raw[raw_start:raw_end + 1], frozenset(), SPAN_CHARS)

    # -- sentences ---------------------------------------------------------------------------------------------
    @staticmethod
    def _closest(tokens: FrozenSet[str], windows: List[Window]) -> Optional[Window]:
        """The window most like `tokens` (F1 of token sets, so a long window does not win just by being long)."""
        if not windows or not tokens:
            return windows[0] if windows else None
        return max(windows, key=lambda w: (2 * len(tokens & w.tokens) / (len(tokens) + len(w.tokens)), -len(w.text)))

    def _sentence_findings(self, answer_text: str, usable: List[str], scored: List[Dict[str, Any]],
                           cited_ids: FrozenSet[str] = frozenset(),
                           warnings: Optional[List[L1Finding]] = None) -> List[L1Finding]:
        messages = self.profile.messages
        windows = [w for norm in usable for w in self._record_windows(norm)]
        all_quantities = set().union(*(w.quantities for w in windows)) if windows else set()
        pattern, stop = self.profile.quantity_pattern, self.profile.stopword_set
        findings: List[L1Finding] = []
        for sentence in split_sentences(answer_text):
            lowered = sentence.lower()
            matches = list(re.finditer(pattern, lowered))
            words = set(_WORD.findall(lowered))
            if not words or (not matches and sentence.rstrip().endswith(":")):
                continue          # nothing to score, or a lead-in line ("...như sau:") that only introduces what follows
            quantity_tokens = {t for m in matches for t in _WORD.findall(m.group())}
            base = words - quantity_tokens - cited_ids       # a record id written in prose is a reference, not a claim
            meaningful = frozenset((base - stop) or base or words)
            hits = {id(w): len(meaningful & w.tokens) for w in windows}
            best = max(windows, key=lambda w: (hits[id(w)], -len(w.text))) if windows else None
            coverage = hits[id(best)] / len(meaningful) if best else 0.0
            shown_claim = clip(sentence, frozenset(), CLAIM_CHARS)
            record = {"sentence": sentence, "coverage": round(coverage, 4), "content_tokens": len(meaningful),
                      "record": self._display_id(best.record_id) if best else "", "quantities": []}
            scored.append(record)
            if best is None or coverage < self.support_threshold:
                near = self._closest(meaningful, windows)
                span = clip(near.text, meaningful, SPAN_CHARS) if near else ""
                doc_id = self._display_id(near.record_id) if near else ""
                unsupported = L1Finding(
                    "claim_unsupported", messages.l1v2_claim.format(claim=shown_claim, doc_id=doc_id, span=span),
                    sentence=sentence, span=span, detail={"coverage": round(coverage, 3), "record": doc_id})
                if self.sentence_support == "block" or warnings is None:
                    findings.append(unsupported)
                    continue
                # warn: keep the finding as a warning and still check this sentence's quantities (those keep blocking)
                warnings.append(unsupported)
                record["support"] = "warned"
            # The sentence is supported. Each of its quantities must sit in a window that matches the words around the
            # quantity (QUANTITY_CONTEXT_TOKENS each side, the clause it governs) as well as any window does: a
            # superset window ties, a window that lacks even one distinguishing word ('tối thiểu' vs 'tối đa') does
            # not. Long sentences that copy several clauses, and sentences with several numbers, are judged per number.
            short = [w for w in windows if w.anchor]
            if not short:
                continue
            tokens = [(m.start(), m.group()) for m in _WORD.finditer(lowered)]
            for match in matches:
                key = _quantity_key(match.group())
                inside = [i for i, (pos, _) in enumerate(tokens) if match.start() <= pos < match.end()]
                lo, hi = max(0, inside[0] - QUANTITY_CONTEXT_TOKENS), inside[-1] + QUANTITY_CONTEXT_TOKENS + 1
                around = {t for _, t in tokens[lo:hi]} - quantity_tokens - cited_ids
                local = frozenset((around - stop) or meaningful)
                local_hits = {id(w): len(local & w.tokens) for w in short}
                top = max(local_hits.values())
                anchors = [w for w in short if local_hits[id(w)] == top]
                if any(key in w.quantities for w in anchors):
                    record["quantities"].append({"quantity": key, "status": "ok"})
                    continue
                kind = "quantity_not_local" if key in all_quantities else "quantity_absent"
                record["quantities"].append({"quantity": key, "status": kind})
                nearest = min(anchors, key=lambda w: len(w.text))
                quantity = re.sub(r"\s+", " ", match.group()).strip()
                findings.append(L1Finding(
                    kind, messages.l1v2_quantity.format(
                        quantity=quantity, claim=shown_claim, doc_id=self._display_id(nearest.record_id),
                        span=clip(nearest.text, local, SPAN_CHARS)),
                    sentence=sentence, span=clip(nearest.text, local, SPAN_CHARS), quantity=quantity,
                    detail={"record": self._display_id(nearest.record_id)}))
                break
        return findings

    def _display_id(self, norm_id: str) -> str:
        """The record id as the corpus writes it."""
        doc = self.valid_article_ids[norm_id]
        return str(doc.get("doc_id") or doc.get("article_id") or doc.get("id") or norm_id)


L1_VERSIONS = ("v1", "v2")


def make_lexical_verifier(corpus: List[Dict[str, Any]], version: str = "v2", *, profile: Optional[DomainProfile] = None,
                          overlap_threshold: float = 0.25,
                          support_threshold: float = DEFAULT_SUPPORT_THRESHOLD,
                          sentence_support: str = "block") -> LexicalGroundingVerifier:
    """The L1 verifier of `verifier.l1_version`: v1 is the original verifier, unchanged (frozen runs); v2 is this module."""
    if version == "v1":
        return LexicalGroundingVerifier(corpus, overlap_threshold=overlap_threshold, profile=profile)
    if version == "v2":
        return LexicalGroundingVerifierV2(corpus, overlap_threshold=overlap_threshold, profile=profile,
                                          support_threshold=support_threshold, sentence_support=sentence_support)
    raise ValueError(f"verifier.l1_version must be one of {list(L1_VERSIONS)}, got {version!r}")


__all__ = ["make_lexical_verifier", "L1_VERSIONS", "LexicalGroundingVerifierV2", "L1Report", "L1Finding", "QuoteCheck", "check_quote", "fold", "source_units",
           "KINDS", "DEFAULT_SUPPORT_THRESHOLD"]
