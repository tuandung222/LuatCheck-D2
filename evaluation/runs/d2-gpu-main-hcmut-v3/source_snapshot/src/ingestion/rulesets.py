"""Structure rulesets.

A ruleset turns normalised text into a tree of `Node`s (hierarchical rulesets) or into a flat list of character
spans (the paragraph/size ruleset). Rulesets are registered by name (`register_ruleset`) so a new domain can add
its own without touching shared code; see docs/plans/ingestion.md.

Built-in rulesets
  vi_legal           Vietnamese regulatory text: Phần / Chương / Mục / Điều N / khoản "1." / điểm "a)" / Phụ lục
  generic_headings   Markdown "#" headings, numbered headings ("1.", "1.1") and Roman numerals ("I.")
  paragraph          paragraph/size-based chunks with overlap (no structure assumed)

Marker lines are only accepted when they continue the numbering of their siblings (a clause "2." must follow
"1." inside the same article, a point "b)" must follow "a)"). Rejected markers stay ordinary text and are counted
in the parse statistics, so wrapped lines such as "15. ..." or "Mục 1 Chương XI của Bộ luật này" inside a
sentence are not mistaken for headings.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type

from .errors import ConfigError

VI_POINT_LETTERS = "abcdđeghiklmnopqrstuvxy"  # Vietnamese legal lettering: no f, j, w, z; đ follows d
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
_VI_ORDINAL_WORDS = {"nhất": 1, "hai": 2, "ba": 3, "tư": 4, "bốn": 4, "năm": 5, "sáu": 6, "bảy": 7, "tám": 8,
                     "chín": 9, "mười": 10}


def roman_to_int(s: str) -> Optional[int]:
    s = s.upper()
    if not s or any(c not in _ROMAN for c in s):
        return None
    total = 0
    for i, c in enumerate(s):
        v = _ROMAN[c]
        total += -v if i + 1 < len(s) and _ROMAN[s[i + 1]] > v else v
    return total


def ascii_slug(s: str) -> str:
    """ASCII identifier fragment; "đ" becomes "dd" so that point "đ)" cannot collide with point "d)"."""
    s = unicodedata.normalize("NFC", s).replace("đ", "dd").replace("Đ", "DD")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


@dataclass
class Node:
    kind: str  # rule name: article, clause, point, chapter, ...
    level: str  # schema level: document/chapter/article/clause/point/section/paragraph
    rank: int  # smaller = higher in the hierarchy
    num: str
    key: tuple
    label: str  # heading text as written (full, continuation lines joined); "" for clause/point
    path_label: str  # element used in section_path / title composition
    start: int  # offset of the first character of the node (heading line or marker line)
    heading_end: int  # offset just after the heading lines (== start when the node has no heading)
    end: int = -1  # end of the subtree (exclusive)
    parent: Optional["Node"] = None
    children: List["Node"] = field(default_factory=list)
    series: int = 1
    ordinal: int = 0  # 1-based position among siblings
    doc_id: str = ""
    title: str = ""


@dataclass
class ParseResult:
    root: Node
    nodes: List[Node]  # document order, root excluded
    stats: Dict[str, Any]
    warnings: List[str]


@dataclass
class Cand:
    kind: str
    level: str
    rank: int
    num: str
    key: tuple
    label: str
    path_label: str
    n_lines: int = 1  # heading lines consumed
    heading: bool = True


class Ctx:
    """Mutable state shared by rules during one parse."""

    def __init__(self):
        self.stack: List[Node] = []
        self.last: Dict[Tuple, tuple] = {}
        self.series: Dict[str, int] = {}
        self.rejected: Dict[str, List[str]] = {}

    def reject(self, kind: str, line: str, offset: int):
        self.rejected.setdefault(kind, []).append(f"@{offset}: {line[:80]}")


class Rule:
    kind = ""
    level = ""
    rank = 0
    parent_kinds: Optional[Tuple[str, ...]] = None  # None = any lower-ranked node
    allow_root = True
    scope = "document"  # sequence counter scope: "document" or "parent"
    policy = "none"  # "none" | "strict" | "monotonic"
    allow_restart = False  # numbering may restart at 1 (a new "series", e.g. an attached regulation)
    max_gap = 10

    def candidate(self, lines: Sequence[str], i: int, ctx: Ctx) -> Optional[Cand]:
        raise NotImplementedError

    def accept(self, cand: Cand, parent: Node, ctx: Ctx) -> Tuple[bool, bool]:
        """Return (accepted, restart)."""
        counter = (cand.kind,) if self.scope == "document" else (cand.kind, id(parent))
        last = ctx.last.get(counter)
        if self.policy == "none":
            return True, False
        if not self._numeric(cand.key):
            return True, False
        n = cand.key[0]
        if self.policy == "strict":
            expected = (last[0] + 1) if last else 1
            return n == expected, False
        # monotonic with a bounded forward gap; restart at 1 starts a new series
        if last is None:
            return n >= 1, False  # the first article may have any number (excerpts start mid-document)
        last_key = last
        if cand.key > last_key and n - last_key[0] <= self.max_gap:
            return True, False
        if self.allow_restart and last and n == 1 and cand.key[1:] in ((), ("",)) and last_key[0] >= 1:
            return True, True
        return False, False

    @staticmethod
    def _numeric(key: tuple) -> bool:
        return bool(key) and isinstance(key[0], int)

    def commit(self, cand: Cand, parent: Node, ctx: Ctx, restart: bool):
        counter = (cand.kind,) if self.scope == "document" else (cand.kind, id(parent))
        if restart:
            ctx.series[cand.kind] = ctx.series.get(cand.kind, 1) + 1
        ctx.last[counter] = cand.key


def _heading_rest(rest: str) -> Optional[str]:
    """Return the heading title found in `rest` or None when `rest` does not look like a heading tail."""
    rest = rest.strip()
    if not rest:
        return ""
    if rest[0] in ".:-–—":
        return rest.lstrip(".:-–— ").strip()
    if rest.isupper():
        return rest
    return None


def _is_upper_title_line(line: str) -> bool:
    return bool(line) and any(c.isalpha() for c in line) and line == line.upper()


def _num_key(raw: str) -> Optional[int]:
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    if raw.lower().startswith("thứ "):
        return _VI_ORDINAL_WORDS.get(raw[4:].strip().lower())
    return roman_to_int(raw)


class _UpperTitleRule(Rule):
    """Rules whose title may sit on the following uppercase line(s): Phần, Chương, Mục, Phụ lục."""
    pattern: re.Pattern
    label_word = ""
    max_title_lines = 5

    def __init__(self, structural: Callable[[str], bool]):
        self._structural = structural

    def candidate(self, lines, i, ctx):
        m = self.pattern.match(lines[i])
        if not m:
            return None
        key_n = _num_key(m.group("num"))
        if key_n is None:
            return None
        title = _heading_rest(m.group("rest") or "")
        if title is None:
            return None
        parts = [title] if title else []
        n = 1
        while (i + n < len(lines) and n < self.max_title_lines + 1 and _is_upper_title_line(lines[i + n])
               and not self._structural(lines[i + n])):
            parts.append(lines[i + n])
            n += 1
        num = m.group("num").strip()
        head = f"{self.label_word} {num}".strip()
        label = (head + " " + " ".join(parts)).strip() if parts else head
        return Cand(self.kind, self.level, self.rank, num, (key_n,), label, label, n)


class PartRule(_UpperTitleRule):
    kind, level, rank = "part", "chapter", 1
    label_word = "Phần"
    policy, allow_restart = "monotonic", True
    pattern = re.compile(r"^(?:PHẦN|Phần)\s+(?P<num>thứ\s+\S+|THỨ\s+\S+|[IVXLC]+|\d+)\b(?P<rest>.*)$")


class ChapterRule(_UpperTitleRule):
    kind, level, rank = "chapter", "chapter", 2
    label_word = "Chương"
    policy, allow_restart = "monotonic", True
    parent_kinds = ("part",)
    pattern = re.compile(r"^(?:CHƯƠNG|Chương)\s+(?P<num>[IVXLC]+|\d+)\b(?P<rest>.*)$")


class SectionRule(_UpperTitleRule):
    kind, level, rank = "muc", "section", 3
    label_word = "Mục"
    policy, scope = "strict", "parent"
    parent_kinds = ("chapter", "appendix")
    pattern = re.compile(r"^(?:MỤC|Mục)\s+(?P<num>\d+|[IVXLC]+)\b(?P<rest>.*)$")


class AppendixRule(_UpperTitleRule):
    kind, level, rank = "appendix", "section", 2
    label_word = "Phụ lục"
    policy, allow_restart = "monotonic", True
    pattern = re.compile(r"^(?:PHỤ LỤC|Phụ lục)\s+(?P<num>\d+|[IVXLC]+)\b(?P<rest>.*)$")


class ArticleRule(Rule):
    kind, level, rank = "article", "article", 4
    parent_kinds = None
    policy, allow_restart = "monotonic", True
    pattern = re.compile(r"^(?:Điều|ĐIỀU)\s+(?P<num>\d{1,4}[a-zđ]?)\s*[.:]\s*(?P<title>.*)$")
    _point_marker = re.compile(r"^[a-zđ]\)")

    def __init__(self, max_gap: int = 10, title_continuation_lines: int = 3):
        self.max_gap = max_gap
        self.title_continuation_lines = title_continuation_lines

    def candidate(self, lines, i, ctx):
        m = self.pattern.match(lines[i])
        if not m:
            return None
        raw = m.group("num")
        digits = re.match(r"\d+", raw).group(0)
        suffix = raw[len(digits):]
        title = m.group("title").strip()
        parts = [title] if title else []
        n = 1
        # A heading wraps onto following lines that start in lower case (a body paragraph starts with a capital
        # letter or a marker). The wrap is only followed while the heading is not yet a complete sentence.
        while (n <= self.title_continuation_lines and i + n < len(lines) and parts
               and not parts[-1].endswith((".", ":", ";"))):
            nxt = lines[i + n]
            if nxt and nxt[0].isalpha() and nxt[0].islower() and not self._point_marker.match(nxt):
                parts.append(nxt)
                n += 1
            else:
                break
        label = f"Điều {raw}." + (" " + " ".join(parts) if parts else "")
        return Cand("article", "article", self.rank, raw, (int(digits), suffix), label, label, n)


class ClauseRule(Rule):
    kind, level, rank = "clause", "clause", 5
    parent_kinds = ("article",)
    allow_root = False
    scope, policy = "parent", "strict"
    pattern = re.compile(r"^(?P<num>\d{1,3})\.(?:\s+(?P<rest>.*))?$")

    def candidate(self, lines, i, ctx):
        m = self.pattern.match(lines[i])
        if not m:
            return None
        num = m.group("num")
        return Cand("clause", "clause", self.rank, num, (int(num),), "", f"Khoản {num}", 1, heading=False)


class PointRule(Rule):
    kind, level, rank = "point", "point", 6
    parent_kinds = ("clause", "article")
    allow_root = False
    scope = "parent"
    pattern = re.compile(r"^(?P<num>[a-zđ])\)(?:\s+(?P<rest>.*))?$")

    def candidate(self, lines, i, ctx):
        m = self.pattern.match(lines[i])
        if not m:
            return None
        letter = m.group("num")
        return Cand("point", "point", self.rank, letter, (VI_POINT_LETTERS.index(letter),) if letter in VI_POINT_LETTERS else (), "",
                    f"Điểm {letter}", 1, heading=False)

    def accept(self, cand, parent, ctx):
        if not cand.key:
            return False, False
        counter = (cand.kind, id(parent))
        last = ctx.last.get(counter)
        expected = (last[0] + 1) if last else 0
        return cand.key[0] == expected, False


# ---------------------------------------------------------------------------------------------- engine

class TreeRuleset:
    """Base class of hierarchical rulesets. Subclasses define `build_rules(options)` and the defaults."""
    name = ""
    kind = "tree"
    defaults: Dict[str, Any] = {}
    default_chunking: Dict[str, Any] = {}
    default_ids: Dict[str, str] = {}
    label_templates: Dict[str, str] = {}

    def __init__(self, options: Optional[Dict[str, Any]] = None):
        merged = dict(self.defaults)
        unknown = set(options or {}) - set(merged)
        if unknown:
            raise ConfigError(f"ruleset {self.name!r}: unknown option(s) {sorted(unknown)}; known: {sorted(merged)}")
        merged.update(options or {})
        self.options = merged
        self.rules: List[Rule] = self.build_rules(merged)
        try:
            self.end_markers = [re.compile(p) for p in merged.get("end_markers", [])]
        except re.error as exc:
            raise ConfigError(f"ruleset {self.name!r}: invalid end_markers regex: {exc}") from exc

    def build_rules(self, options) -> List[Rule]:
        raise NotImplementedError

    def structural(self, line: str) -> bool:
        ctx = Ctx()
        return any(r.candidate([line], 0, ctx) is not None for r in self.rules if r.kind in ("article", "clause", "point"))

    def parse(self, text: str, title: str = "") -> ParseResult:
        lines: List[str] = []
        offsets: List[int] = []
        pos = 0
        for line in text.split("\n"):
            lines.append(line)
            offsets.append(pos)
            pos += len(line) + 1
        root = Node("document", "document", 0, "", (), title, title, 0, 0, end=len(text))
        ctx = Ctx()
        ctx.stack = [root]
        nodes: List[Node] = []
        in_fence = False
        fence_aware = bool(self.options.get("fence_aware"))
        consumed_until = 0
        end_marker_hits = 0
        for i, line in enumerate(lines):
            if i < consumed_until or not line:
                continue
            off = offsets[i]
            if fence_aware and re.match(r"^(```|~~~)", line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if len(ctx.stack) > 1 and any(p.match(line) for p in self.end_markers):
                while len(ctx.stack) > 1:
                    ctx.stack.pop().end = off
                end_marker_hits += 1
                continue
            for rule in self.rules:
                cand = rule.candidate(lines, i, ctx)
                if cand is None:
                    continue
                parent = None
                for node in reversed(ctx.stack):
                    if node.rank < cand.rank:
                        parent = node
                        break
                if parent is None:
                    parent = root
                if rule.parent_kinds is not None:
                    if parent is root:
                        if not rule.allow_root:
                            ctx.reject(rule.kind, line, off)
                            continue
                    elif parent.kind not in rule.parent_kinds:
                        ctx.reject(rule.kind, line, off)
                        continue
                ok, restart = rule.accept(cand, parent, ctx)
                if not ok:
                    ctx.reject(rule.kind, line, off)
                    continue
                rule.commit(cand, parent, ctx, restart)
                while len(ctx.stack) > 1 and ctx.stack[-1].rank >= cand.rank:
                    ctx.stack.pop().end = off
                    # popped nodes keep their recorded end
                heading_end = (offsets[i + cand.n_lines - 1] + len(lines[i + cand.n_lines - 1])) if cand.heading else off
                node = Node(cand.kind, cand.level, cand.rank, cand.num, cand.key, cand.label, cand.path_label,
                            off, heading_end, -1, parent, [], ctx.series.get(cand.kind, 1))
                parent.children.append(node)
                node.ordinal = len(parent.children)
                ctx.stack.append(node)
                nodes.append(node)
                consumed_until = i + cand.n_lines
                break
        while len(ctx.stack) > 1:
            ctx.stack.pop().end = len(text)
        stats = {
            "ruleset": self.name,
            "nodes_by_kind": _count([n.kind for n in nodes]),
            "series": {k: v for k, v in sorted(ctx.series.items())},
            "end_marker_hits": end_marker_hits,
            "rejected_markers": {k: {"count": len(v), "samples": v[:5]} for k, v in sorted(ctx.rejected.items())},
        }
        return ParseResult(root, nodes, stats, [])

    def validate(self, result: ParseResult) -> Tuple[List[str], List[str]]:
        """Ruleset-specific validation -> (errors, warnings)."""
        return [], []


def _count(items: Sequence[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for it in items:
        out[it] = out.get(it, 0) + 1
    return dict(sorted(out.items()))


class ViLegalRuleset(TreeRuleset):
    name = "vi_legal"
    defaults = {
        "max_article_gap": 10,
        "title_continuation_lines": 3,
        "end_markers": [r"^Nơi nhận\s*:", r"^(?:TM|KT|TL|TUQ)\.\s", r"^CHỦ TỊCH QUỐC HỘI", r"^HIỆU TRƯỞNG\s*$"],
        "contiguous_articles": "error",  # error | warn | off
        "series_tags": [],  # id tag per article series, used only when a document has more than one series
        "appendices": True,
    }
    default_chunking = {"granularity": "article", "include_levels": [], "lead_records": True, "lead_in_for": ["clause", "point"],
                        "content_whitespace": "collapse"}
    default_ids = {
        "part": "{prefix}{series_tag}Phan_{num_ascii}",
        "chapter": "{prefix}{series_tag}Chuong_{num_ascii}",
        "muc": "{parent}_Muc_{num_ascii}",
        "appendix": "{prefix}{series_tag}PhuLuc_{num_ascii}",
        "article": "{prefix}{series_tag}Dieu_{num_ascii}",
        "clause": "{parent}_K{num_ascii}",
        "point": "{parent}_{num_ascii}",
        "document": "{prefix}{doc_code}",
    }
    label_templates = {"clause": "Khoản {num}", "point": "Điểm {num}"}

    def build_rules(self, o):
        structural = self.structural
        rules: List[Rule] = [PartRule(structural), ChapterRule(structural), SectionRule(structural)]
        if o["appendices"]:
            rules.append(AppendixRule(structural))
        rules += [ArticleRule(o["max_article_gap"], o["title_continuation_lines"]), ClauseRule(), PointRule()]
        return rules

    def structural(self, line):  # used by title look-ahead: an uppercase line that is itself a heading stops a title
        return bool(re.match(r"^(?:ĐIỀU|CHƯƠNG|MỤC|PHẦN|PHỤ LỤC)\s+(?:\d+|[IVXLC]+\b)", line))

    def validate(self, result):
        errors, warnings = [], []
        mode = self.options["contiguous_articles"]
        if mode == "off":
            return errors, warnings
        series: Dict[int, List[Tuple[int, str]]] = {}
        for n in result.nodes:
            if n.kind == "article":
                series.setdefault(n.series, []).append(n.key)
        sink = errors if mode == "error" else warnings
        for s, keys in sorted(series.items()):
            numbers = [k[0] for k in keys if not k[1]]
            seen = set()
            dup = sorted({x for x in numbers if x in seen or seen.add(x)})
            missing = sorted(set(range(min(numbers), max(numbers) + 1)) - set(numbers)) if numbers else []
            if numbers and min(numbers) != 1:
                warnings.append(f"article series {s} starts at Điều {min(numbers)}, not Điều 1 (partial document?)")
            if missing:
                sink.append(f"article numbering not contiguous in series {s}: missing {missing[:20]}"
                            + (" ..." if len(missing) > 20 else ""))
            if dup:
                sink.append(f"article numbers repeated within series {s}: {dup[:20]}")
        if len(series) > max(1, len(self.options["series_tags"])):
            warnings.append(f"{len(series)} article series found (numbering restarted at 1 {len(series) - 1} time(s)) but "
                            f"only {len(self.options['series_tags'])} series_tags configured; extra series get ids tagged S<n>_")
        return errors, warnings


# ------------------------------------------------------------------------------------ generic headings

class MarkdownHeadingRule(Rule):
    kind, level = "heading", "section"
    pattern = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>\S.*?)\s*#*\s*$")

    def __init__(self, base: int = 0):
        self.base = base

    def candidate(self, lines, i, ctx):
        m = self.pattern.match(lines[i])
        if not m:
            return None
        rank = len(m.group("hashes")) + self.base
        title = m.group("title")
        return Cand(self.kind, self.level, rank, "#" * len(m.group("hashes")), (), title, title)


class _GuardedHeading(Rule):
    kind, level = "heading", "section"

    def __init__(self, max_chars: int, base: int):
        self.max_chars = max_chars
        self.base = base

    def guard(self, title: str) -> bool:
        return (0 < len(title) <= self.max_chars and not title.endswith((".", ";", ":", ",")) and not title[0].islower())


class DecimalHeadingRule(_GuardedHeading):
    pattern = re.compile(r"^(?P<num>\d{1,3}(?:\.\d{1,3})*)\.?\s+(?P<title>\S.*)$")

    def candidate(self, lines, i, ctx):
        m = self.pattern.match(lines[i])
        if not m or not self.guard(m.group("title")):
            return None
        key = tuple(int(x) for x in m.group("num").split("."))
        label = lines[i]
        return Cand(self.kind, self.level, len(key) + self.base, m.group("num"), key, label, label)

    def accept(self, cand, parent, ctx):
        depth = len(cand.key)
        if depth == 1:
            last = ctx.last.get(("decimal", None))
            return cand.key[0] == (last[0] + 1 if last else 1), False
        if parent.kind != "heading" or parent.key != cand.key[:-1]:
            return False, False
        last = ctx.last.get(("decimal", id(parent)))
        return cand.key[-1] == (last[-1] + 1 if last else 1), False

    def commit(self, cand, parent, ctx, restart):
        ctx.last[("decimal", None if len(cand.key) == 1 else id(parent))] = cand.key


class RomanHeadingRule(_GuardedHeading):
    pattern = re.compile(r"^(?P<num>[IVXLC]+)[.)]\s+(?P<title>\S.*)$")

    def candidate(self, lines, i, ctx):
        m = self.pattern.match(lines[i])
        if not m or not self.guard(m.group("title")):
            return None
        n = roman_to_int(m.group("num"))
        if n is None:
            return None
        return Cand(self.kind, self.level, 1 + self.base, m.group("num"), (n,), lines[i], lines[i])

    def accept(self, cand, parent, ctx):
        last = ctx.last.get(("roman",))
        return cand.key[0] == (last[0] + 1 if last else 1), False

    def commit(self, cand, parent, ctx, restart):
        ctx.last[("roman",)] = cand.key


class GenericHeadingsRuleset(TreeRuleset):
    name = "generic_headings"
    defaults = {
        "heading_styles": ["markdown"],
        "heading_max_chars": 100,
        "decimal_rank_offset": 0,
        "fence_aware": True,
        "end_markers": [],
    }
    default_chunking = {"granularity": 1, "include_levels": [], "lead_records": True, "lead_in_for": [],
                        "content_whitespace": "keep"}
    default_ids = {"heading": "{prefix}{doc_code}_S{ordinal_path}", "document": "{prefix}{doc_code}"}
    label_templates = {}

    def build_rules(self, o):
        rules: List[Rule] = []
        for style in o["heading_styles"]:
            if style == "markdown":
                rules.append(MarkdownHeadingRule())
            elif style == "roman":
                rules.append(RomanHeadingRule(o["heading_max_chars"], 0))
            elif style == "decimal":
                rules.append(DecimalHeadingRule(o["heading_max_chars"], o["decimal_rank_offset"] - 0))
            else:
                raise ConfigError(f"generic_headings: unknown heading style {style!r}; use markdown, roman or decimal")
        return rules

    def structural(self, line):
        return False


# ------------------------------------------------------------------------------------- paragraph/size

class ParagraphRuleset:
    """Flat, structure-free chunker: paragraphs are packed up to `max_chars`, consecutive chunks share trailing
    whole paragraphs up to `overlap_chars`. Paragraphs longer than `max_chars` are cut at a sentence end, else at
    whitespace. Every chunk is a contiguous verbatim slice of the normalised text."""
    name = "paragraph"
    kind = "flat"
    defaults = {"max_chars": 1200, "overlap_chars": 150, "paragraph_split": "auto"}
    default_chunking = {"content_whitespace": "keep"}
    default_ids = {"paragraph": "{prefix}{doc_code}_P{n:04d}", "document": "{prefix}{doc_code}"}
    label_templates = {}

    def __init__(self, options: Optional[Dict[str, Any]] = None):
        merged = dict(self.defaults)
        unknown = set(options or {}) - set(merged)
        if unknown:
            raise ConfigError(f"ruleset 'paragraph': unknown option(s) {sorted(unknown)}; known: {sorted(merged)}")
        merged.update(options or {})
        if merged["paragraph_split"] not in ("auto", "blank_line", "line"):
            raise ConfigError("paragraph.paragraph_split must be auto, blank_line or line")
        if merged["max_chars"] < 50 or not 0 <= merged["overlap_chars"] < merged["max_chars"]:
            raise ConfigError("paragraph: need max_chars >= 50 and 0 <= overlap_chars < max_chars")
        self.options = merged

    def validate(self, result):
        return [], []

    def spans(self, text: str) -> List[Tuple[int, int]]:
        max_chars, overlap = self.options["max_chars"], self.options["overlap_chars"]
        split = self.options["paragraph_split"]
        if split == "auto":
            split = "blank_line" if re.search(r"\n[ \t]*\n", text) else "line"
        pattern = re.compile(r"\S(?:.*?\S)?(?=\n[ \t]*\n|\Z)", re.S) if split == "blank_line" else re.compile(r"[^\n]*\S[^\n]*")
        units: List[Tuple[int, int]] = []
        for m in pattern.finditer(text):
            s, e = m.start(), m.end()
            while e - s > max_chars:
                window = text[s:s + max_chars]
                cut = None
                for sm in re.finditer(r"[.!?;:](?=\s)", window):
                    if sm.end() >= max_chars // 2:
                        cut = sm.end()
                if cut is None:
                    ws = [w.start() for w in re.finditer(r"\s", window) if w.start() > 0]
                    cut = ws[-1] if ws else max_chars
                while cut > 1 and text[s + cut - 1].isspace():
                    cut -= 1
                units.append((s, s + cut))
                s += cut
                while s < e and text[s].isspace():
                    s += 1
            if e > s:
                units.append((s, e))
        out: List[Tuple[int, int]] = []
        i = 0
        while i < len(units):
            j = i
            while j + 1 < len(units) and units[j + 1][1] - units[i][0] <= max_chars:
                j += 1
            out.append((units[i][0], units[j][1]))
            if j + 1 >= len(units):
                break
            nxt = j + 1
            for k in range(i + 1, j + 1):
                if units[j][1] - units[k][0] <= overlap:
                    nxt = k
                    break
            i = nxt
        return out


# ------------------------------------------------------------------------------------------- registry

RULESETS: Dict[str, Type] = {}


def register_ruleset(cls: Type) -> Type:
    """Register a ruleset class under `cls.name` (usable as a decorator)."""
    if not getattr(cls, "name", ""):
        raise ConfigError("a ruleset class needs a non-empty `name`")
    RULESETS[cls.name] = cls
    return cls


for _cls in (ViLegalRuleset, GenericHeadingsRuleset, ParagraphRuleset):
    register_ruleset(_cls)


def get_ruleset(name: str, options: Optional[Dict[str, Any]] = None):
    if name not in RULESETS:
        raise ConfigError(f"unknown ruleset {name!r}; registered: {sorted(RULESETS)}")
    return RULESETS[name](options)
