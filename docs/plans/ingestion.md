# Document ingestion pipeline (`src/ingestion`)

Status: implemented, tested on real files (`tests/test_ingestion.py`). Scope: turns source documents into the
corpus JSON the retriever and tools already read, plus a manifest that makes the build auditable. It adds no
model, no network access and no domain knowledge to shared code.

## Why

Until now every corpus came from a one-off script (`docs/materials/benchmark-sources/extract_official_corpus.py`
for the Labour Code, `docs/materials/hcmut-sources/extract_hcmut_corpus.py` for the HCMUT regulations). Each
re-implemented loading, header removal, structure detection and ID rules, and none validated its output. The
labour script also stored 47 of 220 article titles cut off mid-heading (a wrapped heading was read as one line).

The pipeline replaces the per-corpus scripts with one code path driven by a YAML file. Domain specifics (ID
format, heading patterns, granularity, provenance) live in the YAML and in a swappable *ruleset*, not in shared
code (see AGENTS.md, "Direction: domain-general assistant").

## Data flow

```
YAML sources ──► loader ──► normalize ──► ruleset (tree / spans) ──► chunker ──► validate ──► corpus.json + manifest.json
 (path, url,     pdf/docx/   NFC, spaces,   Phần/Chương/Mục/Điều/     granularity,  verbatim,    deterministic
  doc code,      html/md/    running        khoản/điểm | #-headings   ids, lead-in  coverage,    bytes
  ruleset…)      txt         headers,       | paragraphs+overlap      parent_id,    numbering
                             page map                                 section_path
```

| Module | Role |
|---|---|
| `loaders.py` | `load_document(path, fmt, options)` → `LoadedDocument` (raw text per page). PDF via `pypdf` (`extraction_mode="layout"` by default), DOCX via `python-docx`, HTML via the standard-library parser, Markdown/text as UTF-8. A missing optional library raises `MissingDependencyError` naming the package; a PDF without any text layer raises `NoTextLayerError` (OCR is not implemented). |
| `normalize.py` | `normalize(doc, NormalizeConfig)` → `NormalizedDocument`: text, page spans (`pages_for(start, end)`), audit of removed lines. |
| `rulesets.py` | Structure rulesets and the registry (`register_ruleset`, `get_ruleset`). |
| `chunker.py` | Tree/spans → `Chunk` records (granularity, IDs, lead-in, section path, parents, pages). |
| `validate.py` | Per-source and cross-source validation, coverage report. |
| `pipeline.py` | `build(config, root)` → `BuildResult`; `write_outputs`. |
| `__main__.py` | CLI. |

## Chunk schema (`schema.Chunk`)

`Chunk.to_record()` is a flat JSON object. It is a superset of the legacy corpus record, so existing consumers
(`src/retrieval/hybrid_domain.py` reads `doc_id` or `article_id`, `title`/`section_title`, `content`) work unchanged.

| Field | Meaning |
|---|---|
| `doc_id` | Unique record id (template per ruleset/source, see "IDs"). |
| `article_id` | Alias of `doc_id`; present only when `ids.article_id_alias: true` (legacy labour consumers). |
| `collection_id`, `source_name` | Collection the record belongs to; human name of the source document. |
| `title` | Heading as written, wrapped headings joined (`Điều 17. Hành vi … giao kết, thực hiện hợp đồng lao động`). Clauses/points: `<parent title> › Khoản 1 › Điểm a`. |
| `content` | Heading plus the verbatim text of the span (see "Content and whitespace"). |
| `level` | `document`, `chapter`, `article`, `clause`, `point`, `section`, `paragraph`. |
| `parent_id` | Id of the structural parent (article for a clause, clause for a point). With a coarser granularity the parent may not be a record of its own; the manifest counts those (`chunks_with_unemitted_parent`). `null` at the top. |
| `section_path` | Headings of the ancestors, outermost first (`["Chương II VIỆC LÀM, …", "Điều 5. …", "Khoản 1"]`). |
| `lead_in` | For clauses/points (configurable): the lead-in text of the parent, e.g. `1. Người lao động có các quyền sau đây:` for point `a)`. `null` when the parent has none. |
| `source_url`, `source_sha256`, `source_pages` | Provenance. `source_sha256` is computed from the file bytes. `source_pages` are 1-based PDF pages the span touches; `[]` for formats without pages (never invented). |
| `document_number`, `issued_date`, `version` | From the YAML (or `metadata_from`); `null` when not given. |
| `char_start`, `char_end` | Offsets into the normalised document text (`normalized_sha256` in the manifest identifies that text). |
| `doc_code`, `extraction` | Short source code used in ids; one-line description of how the text was produced. |
| extras | Every key under `metadata:` / `metadata_from.fields` (e.g. `law_id`, `law_name`, `scope`, `retrieved_at`, `metadata_verification`) is copied verbatim into the record. They may not collide with schema fields. |

## Normalisation (`normalize.py`)

Formatting only; words are never reordered, dropped or corrected.

* Unicode NFC; NBSP/exotic spaces → space; zero-width characters removed; whitespace runs inside a line folded.
* Line structure is kept (one physical line per source line) because rulesets use it.
* Repeated running headers/footers: a line whose *shape* (digits masked) occurs in the first/last `edge_lines`
  (3) lines of at least `min_page_fraction` (0.3) of the pages and at least `min_pages` (3) pages is removed. Page
  numbers on the edges are removed (`strip_page_numbers`). Everything removed is listed in the manifest
  (`removed_lines`: reason, shape, count, sample). `remove_line_patterns` adds explicit regexes.
  Limit: a legitimately repeated edge line (for example a bare "Chương #" that starts many pages) would be
  removed if it crossed the threshold; raise `min_page_fraction` or disable `remove_repeated_edges` for such files.
* Hyphenation: a soft hyphen (U+00AD) at a line end is joined without a space (unambiguous). A real `-` at a line
  end is joined only with `join_hyphenated: true`, because `lao-` / `động` and date ranges are indistinguishable
  from compounds without a dictionary.
* `blank_lines`: `drop` (default for PDFs), `single` (default otherwise), `keep`.

PDF extraction note: `pypdf`'s default mode splits Vietnamese words (`ng ười`, `vi ệc`) on the Gazette PDF;
`layout` mode does not. The Gazette rebuild matches the old `pdfplumber` output word for word.

## Rulesets

A ruleset is selected per source (`ruleset:`) and configured with `ruleset_options:`.

### `vi_legal` — Vietnamese regulatory structure

Patterns: `Phần …`, `Chương …`, `Mục …`, `Phụ lục …` (appendix), `Điều N.` (with optional letter suffix), clause
`1.`, point `a)` (Vietnamese alphabet `a b c d đ e g …`). Levels/ranks: part(chapter) 1 → chapter 2 / appendix 2 →
Mục 3 → article 4 → clause 5 → point 6.

* **Headings are captured whole.** An article heading continues onto following lines while they start in lower
  case (a body paragraph starts with a capital letter or a marker) and the heading is not yet a sentence
  (`title_continuation_lines`, default 3). Chapter/Mục/appendix titles may be on the following uppercase line(s).
* **Sequence rules.** A clause `N.` must follow `N-1.` inside the same article, a point must follow the previous
  letter, a Mục must follow the previous Mục in its chapter, an article number must increase by at most
  `max_article_gap` (10). A marker that breaks the rule stays ordinary text and is counted
  (`parse.rejected_markers`, with samples, and a manifest warning). This is what stops wrapped lines such as
  `15. …` or `Mục 1 Chương XI của Bộ luật này` from becoming headings.
* **Series.** A decision with an attached regulation restarts article numbering at 1. The restart opens a new
  *series*; `series_tags` (e.g. `["QD_", ""]`) give the series distinct ids. Without enough tags, extra series
  get `S<n>_` and the manifest warns.
* **End markers.** `end_markers` (regexes at line start) close all open nodes: `Nơi nhận:`, `TM.`/`KT.`/`TL.`,
  `CHỦ TỊCH QUỐC HỘI`, a lone `HIỆU TRƯỞNG`. The Labour config overrides them with just `CHỦ TỊCH QUỐC HỘI`.
* **Validation.** Article numbers must be contiguous between the first and last article of each series
  (`contiguous_articles: error|warn|off`); starting above 1 only warns (excerpts).

### `generic_headings`

Markdown `#` headings (rank = number of `#`; fenced code is skipped), Roman numerals (`I.`) and numbered headings
(`1.`, `1.1`), chosen with `heading_styles` (default `["markdown"]`). Numbered/Roman headings are guarded
(`heading_max_chars`, must not end in `. ; : ,`, must not start in lower case) and must continue their sequence.
HTML headings and DOCX `Heading N` styles are converted by the loaders to Markdown `#` markers (a structural
marker, not a text rewrite; switch off with `loader: {headings_as_markdown: false}`). All nodes have level
`section`, so granularity is given as the integer rank.

### `paragraph`

No structure assumed. Paragraphs (`paragraph_split`: `blank_line`, `line` or `auto`) are packed up to
`max_chars` (1200); consecutive chunks share trailing whole paragraphs up to `overlap_chars` (150); a paragraph
longer than `max_chars` is cut at a sentence end, else whitespace. Ids `<doc_code>_P0001…`, level `paragraph`.

## Granularity

`chunking:` options (defaults come from the ruleset):

| Option | Meaning |
|---|---|
| `granularity` | Level at which records are emitted: `article`, `clause`, `point`, `chapter`, `section`, `document`, or an integer rank (generic headings). |
| `include_levels` | Also emit these (shallower) levels; with `granularity: clause, include_levels: [article]` you get article records and clause children linked by `parent_id`. |
| `lead_records` (true) | A shallower parent that is not emitted but has text before its first child (heading + lead-in sentence) is emitted as `<id>_lead`, so clause/point corpora still cover it. A parent that is only a heading is not emitted; its text is in the children's `title`/`section_path`. |
| `lead_in_for` | Chunk levels that get `lead_in` (`[clause, point]` for `vi_legal`). |
| `content_whitespace` | `collapse` (single spaces, the legacy corpus format) or `keep` (line breaks preserved). |
| `preamble_record` (false) | Emit the text before the first heading as `<id>_preamble`. |
| `on_no_structure` | `error` (default), `document` or `paragraph`: what to do when the ruleset finds nothing at the granularity. The fallback is recorded in the manifest (`fallback_chunking`), never silent. |

A shallower node with no children is always emitted (an article without clauses at clause granularity), so no text
is dropped silently.

## IDs

Templates are per ruleset (`ids.templates` overrides single keys). Variables: `{prefix}` (`ids.prefix`),
`{doc_code}`, `{num}`, `{num_ascii}` (ASCII slug; `đ` → `dd` so points `d)` and `đ)` cannot collide), `{parent}`
(parent's full id), `{series_tag}`, `{ordinal_path}`, `{n}`. `vi_legal` defaults: `Dieu_<n>`, clause
`<article>_K<n>`, point `<clause>_<letter>`, `Chuong_<n>`, `Muc_<n>`, `PhuLuc_<n>`. The Labour config sets
`article: "Dieu_{num}"`; the HCMUT config uses `HCMUT_<doc_code>_<series_tag>Dieu_<n>`. Ids must be unique across
the whole output file (validation error otherwise).

## Validation and manifest

Per chunk: non-empty id/title/content; valid level; offsets in range; the content equals the normalised-text slice
at its offsets **and** is found by substring search in the normalised text (whitespace-folded on both sides for
`collapse`); page numbers exist. Per source: coverage (character and non-whitespace fractions, plus the uncovered
stretches that contain text, first 25 listed with a preview), ruleset checks (article contiguity), warnings
(rejected markers, tables flattened, pages without text, over-long titles). Corpus: unique ids. Any error makes
`status: failed`: the manifest is still written (a failed build is evidence), the corpus is not.

Manifest (`schema_version`, `tool`, `status`, `config` {path, sha256, output, defaults}, `environment` {python,
library versions}, `sources[]`, `totals`, `errors`, `warnings`, `output` {corpus path, record count, corpus
sha256}). Each source entry has input path/sha256/bytes, format, the resolved ruleset/normalize/chunking/id
parameters, loader info, `normalized_sha256`, removed running lines, parse statistics, record counts per level,
validation (coverage, errors, warnings) and, when used, the `metadata_from` file and its sha256. Nothing
time-dependent is recorded, so the same inputs give byte-identical corpus and manifest.

## CLI

```
.venv/bin/python -m src.ingestion build --config config/ingestion/<name>.yaml [--root DIR] [--check] [--overwrite]
```

`--root` is the directory source/output paths are relative to (default: the current directory). `--check`
rebuilds in memory and compares with the files on disk (exit 1 on difference; use it in CI). Exit codes: 0 ok,
1 `--check` difference, 2 configuration/ingestion/validation error. A corpus file that exists and is not an
untouched output of this tool (no manifest with a matching hash) is **never overwritten** unless `--overwrite`,
which protects hand-built or frozen corpora such as `data/corpus/labor_code_2019_official.json`.

### Config format

```yaml
version: 1
output: {corpus: data/corpus/x.json, manifest: data/corpus/x.manifest.json}
defaults: {...}            # deep-merged under every source
sources:
  - path: docs/.../file.pdf          # required
    url: https://...                 # source_url
    format: pdf                      # optional; inferred from the suffix
    collection_id: ...   doc_code: ...   source_name: ...   title: ...
    document_number: ...   issued_date: ...   version: ...
    ruleset: vi_legal                # vi_legal | generic_headings | paragraph | registered name
    ruleset_options: {...}
    loader: {mode: layout}           # per-format loader options
    normalize: {...}                 # NormalizeConfig fields
    chunking: {...}
    ids: {prefix: "", templates: {...}, article_id_alias: false}
    metadata: {law_id: ..., scope: ...}      # copied into every record
    metadata_from: {file: ..., records_key: documents, match: {doc_code: X}, fields: {url: source_url, ...},
                    verify_sha256_field: sha256}
    min_coverage: 0.9                # optional hard floor for non-whitespace coverage
```

`metadata_from` reads provenance from a collection manifest instead of retyping it, and with
`verify_sha256_field` the build fails if the PDF's hash differs from the one recorded there.

## Shipped configs

* `config/ingestion/labor_code_2019.yaml` → `data/corpus/labor_code_2019_ingested.json` (+ `.manifest.json`).
  Rebuilt from `bll2019-congbao.pdf`: 220 articles, ids `Dieu_1…Dieu_220`, `article_id` alias kept.
  Compared with the frozen `labor_code_2019_official.json`: identical ids, identical `content` for all 220,
  47 titles extended to the full heading, `source_pages` differ for 4 articles (the old script also counted a
  following page that only holds the next chapter/Mục heading), non-whitespace coverage 98.9 % (cover block,
  chapter/Mục headings, signature). The frozen file is not touched.
* `config/ingestion/hcmut_academic.yaml` → `data/corpus/hcmut_academic_ingested.json`. Ten included PDFs of
  `docs/materials/hcmut-sources/`; provenance from its `manifest.json`. Article/appendix granularity gives 114
  records whose ids are a subset of `hcmut_academic_v1.json` (v1 additionally splits long amending articles at
  quoted decimal clauses `3.1`, 29 records, which this config does not). `hcmut_academic_v1.json` is not touched.

## Adding a domain

1. **Config only** (most cases): choose `generic_headings` or `paragraph`, or `vi_legal` with other
   `ruleset_options`/`ids.templates`, and write `config/ingestion/<domain>.yaml`.
2. **New structure**: subclass `TreeRuleset` (see `ViLegalRuleset`, `GenericHeadingsRuleset`), define `name`,
   `defaults` (options), `default_chunking`, `default_ids`, `label_templates`, `build_rules(options)`, and optionally
   `validate(result)`; decorate with `@register_ruleset` in a module that is imported before `build` (for example from
   a domain package). A `Rule` implements `candidate(lines, i, ctx)` (returns a `Cand` with level, rank, number,
   label) and optionally `accept` for sequence checks. `tests/test_ingestion.py::test_new_domain_ruleset_can_be_registered`
   is a working example.
3. **Domain profile**: the tool names, prompts and ID conventions the agent uses stay in `config/domains/*.yaml`; the
   corpus produced here only has to use ids matching the profile's `ids.pattern`.
4. A new domain still needs its own reviewed tasks and evaluation before any claim about it (AGENTS.md).

## Known limits

* **Scanned PDFs need OCR.** Image-only PDFs raise `NoTextLayerError`; partially scanned PDFs produce a manifest warning naming the pages without text, and that content is missing from
  the corpus. OCR is not implemented.
* **Tables.** PDF tables are whatever `pypdf` layout text gives (cells separated by spaces, row alignment may
  break); DOCX/HTML tables are flattened to one line per row with ` | `; no cell structure, no header detection.
  Appendices that are mostly tables become one flat record.
* **Multi-column PDFs, footnotes, text boxes, DOCX headers/footers, images, math** are not handled specially.
* **Heading continuation** relies on lower-case continuation lines; a wrapped heading whose continuation starts
  with a capital letter is cut at the line break, and a body paragraph that starts in lower case right after a
  heading would be absorbed (validation warns when a title exceeds 250 characters).
* **Quoted amendments.** In amending decisions the quoted base clauses can contain their own `Điều`/`1.`/`a)`
  markers. Sequence rules reject most of them but a quoted heading that happens to continue the numbering can be
  taken as a real one; such text is reported in `rejected_markers` and the contiguity check.
* **Sequence assumptions.** Numbering that skips (repealed clauses written without a number, `Điều 5a`
  suffixes beyond one letter) is tolerated only within `max_article_gap` for articles; clauses and points must be
  consecutive.
* **Running headers** are detected by repetition; a document with a unique first-page header keeps it.
* **Content representation.** `collapse` loses line breaks inside a record; use `keep` where layout matters.
* **No semantic checks.** Verbatim-ness is checked against the normalised text, not against the original PDF
  rendering; a loader that mis-extracts a word reproduces that error consistently (the Gazette rebuild was compared
  with an independent extractor's output for this reason).
* **Language.** `vi_legal` is Vietnamese-specific by design; other languages need their own ruleset.
* Dependencies: `pypdf` (already in `requirements.txt`) and `PyYAML` always; `python-docx` only for `.docx`
  (`uv pip install python-docx`); HTML uses the standard library.
