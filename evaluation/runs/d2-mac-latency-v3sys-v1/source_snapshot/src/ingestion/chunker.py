"""Turn a parsed structure tree (or flat spans) into `Chunk` records.

Granularity
  `granularity` is the level at which records are emitted: a level name (article, clause, point, chapter,
  section, ...) or, for rulesets whose nodes all share one level name (generic headings), an integer rank.
  Leaf nodes shallower than the target (an article without numbered clauses when granularity is `clause`) are
  emitted themselves, so no text is silently dropped.
  `include_levels` additionally emits those levels (e.g. granularity=clause, include_levels=[article] gives
  article records plus clause children linked by parent_id).
  `lead_records` emits the text a non-emitted parent has before its first child (its heading and lead-in
  sentence) as a separate `<id>_lead` record, so clause-level corpora still cover the article preambles.

Every record's `content` is a contiguous slice of the normalised text (heading included); with
`content_whitespace: collapse` runs of whitespace (including line breaks) are folded to single spaces, which is
the representation the legacy corpus uses.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .errors import ConfigError
from .normalize import NormalizedDocument
from .rulesets import Node, ParagraphRuleset, ParseResult, TreeRuleset, ascii_slug
from .schema import Chunk, LEVELS

CHUNKING_KEYS = {"granularity", "include_levels", "lead_records", "lead_in_for", "content_whitespace",
                 "preamble_record", "on_no_structure", "fallback_paragraph"}


def resolve_chunking(ruleset, overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cfg = {"granularity": None, "include_levels": [], "lead_records": True, "lead_in_for": [],
           "content_whitespace": "keep", "preamble_record": False, "on_no_structure": "error",
           "fallback_paragraph": {}}
    cfg.update(ruleset.default_chunking)
    unknown = set(overrides or {}) - CHUNKING_KEYS
    if unknown:
        raise ConfigError(f"unknown chunking option(s) {sorted(unknown)}; known: {sorted(CHUNKING_KEYS)}")
    cfg.update(overrides or {})
    if cfg["content_whitespace"] not in ("keep", "collapse"):
        raise ConfigError("chunking.content_whitespace must be keep or collapse")
    if cfg["on_no_structure"] not in ("error", "document", "paragraph"):
        raise ConfigError("chunking.on_no_structure must be error, document or paragraph")
    for lvl in list(cfg["include_levels"]) + list(cfg["lead_in_for"]):
        if lvl not in LEVELS:
            raise ConfigError(f"unknown level {lvl!r}; levels: {LEVELS}")
    g = cfg["granularity"]
    if isinstance(ruleset, TreeRuleset) and g is None:
        raise ConfigError("chunking.granularity is required")
    if isinstance(g, str) and g not in LEVELS:
        raise ConfigError(f"chunking.granularity {g!r} must be one of {LEVELS} or an integer rank")
    return cfg


def _fold(s: str, mode: str) -> str:
    return " ".join(s.split()) if mode == "collapse" else s


def _strip_span(text: str, start: int, end: int) -> Tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


class IdContext:
    """Computes record ids from the templates of the ruleset, overridable per source."""

    def __init__(self, ruleset, overrides: Optional[Dict[str, str]], prefix: str, doc_code: str, tags: List[str]):
        self.templates = dict(ruleset.default_ids)
        unknown = set(overrides or {}) - set(self.templates)
        if unknown:
            raise ConfigError(f"ids.templates: unknown key(s) {sorted(unknown)}; known: {sorted(self.templates)}")
        self.templates.update(overrides or {})
        self.prefix, self.doc_code, self.tags = prefix, doc_code, tags

    def format(self, key: str, **vars_) -> str:
        base = {"prefix": self.prefix, "doc_code": self.doc_code, "parent": "", "series_tag": "", "num": "",
                "num_ascii": "", "ordinal_path": "", "n": 0}
        base.update(vars_)
        try:
            return self.templates[key].format_map(base).lstrip("_")
        except (KeyError, IndexError, ValueError) as exc:
            raise ConfigError(f"bad id template for {key!r} ({self.templates[key]!r}): {exc!r}") from exc

    def series_tag(self, series: int, total: int) -> str:
        if total <= 1:
            return ""
        return self.tags[series - 1] if series - 1 < len(self.tags) else f"S{series}_"


def assign_ids(result: ParseResult, ids: IdContext, title: str) -> None:
    totals = result.stats.get("series", {})
    root = result.root
    root.doc_id = ids.format("document")
    root.title = title

    def visit(node: Node, path: List[int]):
        for child in node.children:
            p = path + [child.ordinal]
            key = child.kind if child.kind in ids.templates else ("heading" if "heading" in ids.templates else child.kind)
            child.doc_id = ids.format(
                key, num=child.num, num_ascii=ascii_slug(child.num) or str(child.ordinal),
                parent=node.doc_id if node is not root else "", ordinal_path="_".join(map(str, p)),
                series_tag=ids.series_tag(child.series, totals.get(child.kind, 1)))
            child.title = child.label if child.label else (f"{node.title} › {child.path_label}" if node is not root else child.path_label)
            visit(child, p)

    visit(root, [])


def _lead_span(node: Node, text: str) -> Optional[Tuple[int, int]]:
    if not node.children:
        return None
    s, e = _strip_span(text, node.heading_end, node.children[0].start)
    return (s, e) if e > s else None


def _ancestors(node: Node) -> List[Node]:
    chain = []
    p = node.parent
    while p is not None and p.parent is not None:
        chain.append(p)
        p = p.parent
    return list(reversed(chain))


def build_tree_chunks(norm: NormalizedDocument, result: ParseResult, cfg: Dict[str, Any], base: Dict[str, Any],
                      alias_article_id: bool) -> List[Chunk]:
    text = norm.text
    g = cfg["granularity"]
    mode = cfg["content_whitespace"]
    include = set(cfg["include_levels"])
    nodes = result.nodes

    def is_target(n: Node) -> bool:
        return n.rank == g if isinstance(g, int) else n.level == g

    emitted: List[Tuple[Node, str]] = []  # (node, "node" | "lead")

    def walk(n: Node) -> None:
        body = bool(text[n.heading_end:n.end].strip())
        if is_target(n) or n.level in include or (not n.children and body):
            emitted.append((n, "node"))  # target, explicitly included level, or a leaf shallower than the target
        elif cfg["lead_records"] and n.children and _lead_span(n, text):
            emitted.append((n, "lead"))
        if is_target(n):
            return  # the record already holds the whole subtree
        for c in n.children:
            walk(c)

    if g == "document":
        emitted.append((result.root, "node"))
    else:
        for top in result.root.children:
            walk(top)
        if cfg["preamble_record"] and nodes:
            s0, e0 = _strip_span(text, 0, nodes[0].start)
            if e0 > s0:
                emitted.insert(0, (result.root, "lead"))
    chunks: List[Chunk] = []
    for node, kind in emitted:
        if kind == "lead" and node is result.root:
            s, e = _strip_span(text, 0, nodes[0].start)
            doc_id, title, level = node.doc_id + "_preamble", node.title, "document"
            parent_id, path = None, []
        elif kind == "lead":
            s, e = _strip_span(text, node.start, node.children[0].start)
            doc_id, title, level = node.doc_id + "_lead", node.title, node.level
            parent_id = _parent_ref(node.parent, result.root, emitted_ids=None)
            path = [a.path_label for a in _ancestors(node)]
        else:
            s, e = _strip_span(text, node.start, node.end)
            doc_id, title, level = node.doc_id, node.title, node.level
            parent_id = _parent_ref(node.parent, result.root, emitted_ids=None)
            path = [a.path_label for a in _ancestors(node)]
        lead_in = None
        if kind == "node" and node is not result.root and level in cfg["lead_in_for"] and node.parent is not result.root:
            span = _lead_span(node.parent, text)
            lead_in = _fold(text[span[0]:span[1]], mode) if span else None
        chunks.append(Chunk(
            doc_id=doc_id, title=title, content=_fold(text[s:e], mode), level=level, parent_id=parent_id,
            section_path=path, lead_in=lead_in, source_pages=norm.pages_for(s, e), char_start=s, char_end=e,
            article_id=doc_id if alias_article_id else None, **base))
    return chunks


def _parent_ref(parent: Optional[Node], root: Node, emitted_ids) -> Optional[str]:
    """parent_id: the structural parent when it is an addressable unit (article/clause/point/section/chapter),
    never the synthetic document root."""
    if parent is None or parent is root:
        return None
    return parent.doc_id


def build_flat_chunks(norm: NormalizedDocument, ruleset: ParagraphRuleset, cfg: Dict[str, Any], base: Dict[str, Any],
                      ids: IdContext, title: str, alias_article_id: bool) -> List[Chunk]:
    text, mode = norm.text, cfg["content_whitespace"]
    chunks = []
    for n, (s, e) in enumerate(ruleset.spans(text), 1):
        s, e = _strip_span(text, s, e)
        doc_id = ids.format("paragraph", n=n)
        chunks.append(Chunk(
            doc_id=doc_id, title=f"{title} #{n}", content=_fold(text[s:e], mode), level="paragraph", parent_id=None,
            section_path=[], source_pages=norm.pages_for(s, e), char_start=s, char_end=e,
            article_id=doc_id if alias_article_id else None, **base))
    return chunks


def build_document_chunk(norm: NormalizedDocument, cfg: Dict[str, Any], base: Dict[str, Any], doc_id: str, title: str,
                         alias_article_id: bool) -> List[Chunk]:
    text = norm.text
    s, e = _strip_span(text, 0, len(text))
    return [Chunk(doc_id=doc_id, title=title, content=_fold(text[s:e], cfg["content_whitespace"]), level="document",
                  parent_id=None, section_path=[], source_pages=norm.pages_for(s, e), char_start=s, char_end=e,
                  article_id=doc_id if alias_article_id else None, **base)]
