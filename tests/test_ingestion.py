"""Ingestion pipeline tests on real files: the Official Gazette PDF, the HCMUT regulation PDFs and small verbatim
excerpts under tests/fixtures/ingestion/. Real loaders, rulesets, validators and CLI; no substitutions.
Temporary directories are used only for outputs and for config files that point at real sources."""
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest
import yaml

from src.ingestion import (ConfigError, IngestionError, MissingDependencyError, NoTextLayerError, build,
                           register_ruleset, write_outputs)
from src.ingestion import loaders, rulesets
from src.ingestion.normalize import NormalizeConfig, normalize
from src.ingestion.pipeline import sha256_file
from src.ingestion.rulesets import GenericHeadingsRuleset

ROOT = Path(__file__).resolve().parents[1]
FIX = "tests/fixtures/ingestion"
LABOUR_CFG = ROOT / "config/ingestion/labor_code_2019.yaml"
HCMUT_CFG = ROOT / "config/ingestion/hcmut_academic.yaml"
FROZEN = ROOT / "data/corpus/labor_code_2019_official.json"
FROZEN_MANIFEST = ROOT / "docs/materials/benchmark-sources/corpus_manifest.json"
GAZETTE = ROOT / "docs/materials/benchmark-sources/bll2019-congbao.pdf"


def fold(s):
    return " ".join(s.split())


def run_config(tmp_path, sources, defaults=None, name="cfg.yaml"):
    """Write a real ingestion YAML into a temp dir (outputs there too) and build it against the repo root."""
    cfg = {"version": 1, "output": {"corpus": str(tmp_path / "out.json"), "manifest": str(tmp_path / "out.manifest.json")},
           "defaults": defaults or {}, "sources": sources}
    path = tmp_path / name
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return build(path, ROOT)


@pytest.fixture(scope="module")
def frozen():
    return json.loads(FROZEN.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def labour():
    return build(LABOUR_CFG, ROOT)


# ------------------------------------------------------------------------------- labour rebuild

def test_frozen_corpus_is_the_pinned_one():
    pinned = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))["corpus_sha256"]
    assert sha256_file(FROZEN) == pinned


def test_labour_rebuild_ids_and_content_match_frozen(labour, frozen):
    assert labour.ok, labour.errors
    new = labour.records
    assert [r["article_id"] for r in new] == [r["article_id"] for r in frozen]
    assert len(new) == 220 and [r["doc_id"] for r in new] == [r["article_id"] for r in new]
    differing = [(a["article_id"], a["content"], b["content"]) for a, b in zip(frozen, new) if a["content"] != b["content"]]
    # Observed on the Gazette PDF: content is identical for all 220 articles. Any difference must be explained, so the
    # assertion lists them instead of silently tolerating drift.
    assert differing == [], f"{len(differing)} article(s) differ from the frozen extraction: {[d[0] for d in differing][:10]}"
    for a, b in zip(frozen, new):
        for key in ("source_url", "source_sha256", "law_id", "law_name", "scope"):
            assert a[key] == b[key], (a["article_id"], key)


def test_labour_titles_recovered(labour, frozen):
    new = labour.records
    changed = [(a, b) for a, b in zip(frozen, new) if a["title"] != b["title"]]
    # the frozen titles stop mid-heading in 47 records; every difference is a strict extension of the frozen title
    assert len(changed) == 47
    for old, rec in changed:
        assert rec["title"].startswith(old["title"]) and len(rec["title"]) > len(old["title"]), old["article_id"]
        assert old["content"].startswith(rec["title"]), "frozen content already contains the full heading"
        tail = rec["title"][len(old["title"]):].strip()
        assert tail and tail[0].islower(), (old["article_id"], tail)  # continuation of a wrapped heading
    # nothing is left truncated: after a title, the article body starts with a capital letter, a digit or a marker
    for rec in new:
        assert rec["content"].startswith(rec["title"])
        body = rec["content"][len(rec["title"]):].strip()
        assert not body or not body[0].islower(), (rec["article_id"], body[:40])
    assert next(r for r in new if r["doc_id"] == "Dieu_17")["title"] == \
        "Điều 17. Hành vi người sử dụng lao động không được làm khi giao kết, thực hiện hợp đồng lao động"


def test_labour_source_pages_match_except_trailing_heading_pages(labour, frozen):
    loaded = loaders.load_document(GAZETTE, "pdf", {})
    norm = normalize(loaded, NormalizeConfig())
    texts = {n: norm.text[s:e] for n, s, e in norm.page_spans}
    differences = [(a, b) for a, b in zip(frozen, labour.records) if a["source_pages"] != b["source_pages"]]
    assert 0 < len(differences) <= 10
    for old, rec in differences:
        assert set(rec["source_pages"]) < set(old["source_pages"]), old["article_id"]
        # the frozen script counted a following page that only carries the next chapter/section heading
        extra = sorted(set(old["source_pages"]) - set(rec["source_pages"]))
        assert extra == [rec["source_pages"][-1] + 1]
        assert texts[extra[0]].startswith(("Chương", "Mục")), (old["article_id"], texts[extra[0]][:40])


def test_labour_validation_manifest_and_provenance(labour):
    m = labour.manifest
    assert m["status"] == "ok" and m["errors"] == []
    src = m["sources"][0]
    assert src["sha256"] == sha256_file(GAZETTE)
    assert src["validation"]["verbatim_chunks"] == 220 and src["validation"]["errors"] == []
    cov = src["validation"]["coverage"]
    assert cov["non_whitespace_fraction"] > 0.98  # remainder: cover block, chapter/section headings, signature
    assert all("Chương" in g["preview"] or "Mục" in g["preview"] or g["start"] == 0 or "CHỦ TỊCH" in g["preview"]
               for g in cov["uncovered_listed"])
    assert src["parse"]["nodes_by_kind"]["article"] == 220 and src["parse"]["series"] == {}
    assert m["environment"]["libraries"]["pypdf"] and m["environment"]["libraries"]["PyYAML"]
    assert {r["reason"] for r in src["removed_lines"]} == {"repeated_edge_line"}
    assert sum(r["count"] for r in src["removed_lines"]) == 93  # one Gazette header on each of 93 pages with text
    assert m["output"]["records"] == 220
    assert m["output"]["corpus_sha256"] == hashlib.sha256(labour.corpus_text.encode("utf-8")).hexdigest()
    assert "generated_at" not in json.dumps(m)  # nothing time-dependent, so reruns are byte-identical


def test_labour_build_is_deterministic(labour):
    again = build(LABOUR_CFG, ROOT)
    assert again.corpus_text == labour.corpus_text
    assert again.manifest_text == labour.manifest_text


def test_cli_writes_outputs_that_equal_the_in_memory_build(tmp_path, labour):
    cfg = yaml.safe_load(LABOUR_CFG.read_text(encoding="utf-8"))
    cfg["output"] = {"corpus": str(tmp_path / "labour.json"), "manifest": str(tmp_path / "labour.manifest.json")}
    cfg_path = tmp_path / "labour.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    cmd = [sys.executable, "-m", "src.ingestion", "build", "--config", str(cfg_path), "--root", str(ROOT)]
    done = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    assert "status=ok" in done.stdout and "records=220" in done.stdout
    assert (tmp_path / "labour.json").read_text(encoding="utf-8") == labour.corpus_text
    check = subprocess.run(cmd + ["--check"], capture_output=True, text=True, env=env, cwd=tmp_path)
    assert check.returncode == 0 and "up to date" in check.stdout
    # the shipped config writes to a new path and never to the frozen corpus
    shipped = yaml.safe_load(LABOUR_CFG.read_text(encoding="utf-8"))["output"]
    assert shipped["corpus"] == "data/corpus/labor_code_2019_ingested.json"
    assert FROZEN.name not in json.dumps(shipped)


def test_refuses_to_overwrite_a_corpus_it_did_not_write(tmp_path):
    victim = tmp_path / "hand_made_corpus.json"
    victim.write_bytes(FROZEN.read_bytes())
    before = victim.read_bytes()
    result = build_fixture_txt(tmp_path, out=victim)
    with pytest.raises(IngestionError, match="refusing to overwrite"):
        write_outputs(result, ROOT)
    assert victim.read_bytes() == before
    written, _ = write_outputs(result, ROOT, overwrite=True)  # explicit opt-in works
    assert written == victim and victim.read_bytes() != before


def build_fixture_txt(tmp_path, out=None):
    cfg = {"version": 1, "output": {"corpus": str(out or tmp_path / "o.json"), "manifest": str(tmp_path / "o.manifest.json")},
           "sources": [{"path": f"{FIX}/labour_chuong1_dieu3_6.txt", "doc_code": "BLL2019_EXCERPT", "ruleset": "vi_legal",
                        "chunking": {"granularity": "article"}}]}
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return build(p, ROOT)


# --------------------------------------------------------------------------- hierarchy and granularity

def legal_source(path, **chunking):
    return {"path": f"{FIX}/{path}", "doc_code": "BLL2019", "collection_id": "labor_code_2019", "ruleset": "vi_legal",
            "ids": {"templates": {"article": "Dieu_{num}"}}, "chunking": chunking}


def test_article_level_text_excerpt_equals_frozen_records(tmp_path, frozen):
    r = run_config(tmp_path, [legal_source("labour_chuong1_dieu3_6.txt", granularity="article", content_whitespace="collapse")])
    assert r.ok, r.errors
    by_id = {x["article_id"]: x for x in frozen}
    assert [c.doc_id for c in r.chunks] == ["Dieu_3", "Dieu_4", "Dieu_5", "Dieu_6"]
    for c in r.chunks:
        assert c.content == by_id[c.doc_id]["content"]  # same text as the PDF-derived record
        assert c.section_path == ["Chương I NHỮNG QUY ĐỊNH CHUNG"] and c.parent_id == "Chuong_I"
        assert c.source_pages == []  # a text file has no pages; none are invented
    assert any("starts at Điều 3" in w for w in r.manifest["warnings"])


def test_clause_and_point_granularity_keep_lead_in_and_parents(tmp_path, frozen):
    src = legal_source("labour_chuong1_dieu3_6.txt", granularity="point", include_levels=["article"],
                       lead_in_for=["clause", "point"], content_whitespace="collapse")
    r = run_config(tmp_path, [src])
    assert r.ok, r.errors
    ids = {c.doc_id: c for c in r.chunks}
    point = ids["Dieu_5_K1_a"]
    assert point.level == "point" and point.parent_id == "Dieu_5_K1"
    assert point.lead_in == "1. Người lao động có các quyền sau đây:"
    assert point.section_path[-2:] == ["Điều 5. Quyền và nghĩa vụ của người lao động", "Khoản 1"]
    assert point.title == "Điều 5. Quyền và nghĩa vụ của người lao động › Khoản 1 › Điểm a"
    assert point.content.startswith("a) Làm việc;") and point.content in frozen_article(frozen, "Dieu_5")
    # the accented point letter gets a distinct ascii id; no id collides
    assert "Dieu_5_K1_dd" in ids and "Dieu_5_K1_d" in ids
    # the clause that owns the points survives as a lead record (its text is not lost at point granularity)
    lead = ids["Dieu_5_K1_lead"]
    assert lead.content == "1. Người lao động có các quyền sau đây:" and lead.level == "clause"
    assert ids["Dieu_5"].level == "article" and ids["Dieu_5"].parent_id == "Chuong_I"
    # clauses without points are emitted themselves (leaf fallback)
    assert ids["Dieu_4_K1"].level == "clause" and ids["Dieu_4_K1"].lead_in is None and "Dieu_5_K2_lead" in ids
    # char offsets are real offsets into the normalised text
    assert r.manifest["sources"][0]["validation"]["verbatim_chunks"] == len(r.chunks)

    clause = run_config(tmp_path, [legal_source("labour_chuong1_dieu3_6.txt", granularity="clause", content_whitespace="collapse")])
    assert clause.ok and not any(c.level == "point" for c in clause.chunks)
    k1 = next(c for c in clause.chunks if c.doc_id == "Dieu_5_K1")
    assert "a) Làm việc;" in k1.content and k1.parent_id == "Dieu_5"  # parent is referenced even when not emitted
    assert clause.manifest["sources"][0]["validation"]["chunks_with_unemitted_parent"] > 0


def frozen_article(frozen, doc_id):
    return next(r for r in frozen if r["article_id"] == doc_id)["content"]


def test_wrapped_headings_are_captured_whole(tmp_path, frozen):
    r = run_config(tmp_path, [legal_source("labour_dieu17_18.txt", granularity="article", content_whitespace="collapse")])
    assert r.ok, r.errors
    a17 = next(c for c in r.chunks if c.doc_id == "Dieu_17")
    assert a17.title == "Điều 17. Hành vi người sử dụng lao động không được làm khi giao kết, thực hiện hợp đồng lao động"
    assert a17.section_path == ["Chương III HỢP ĐỒNG LAO ĐỘNG", "Mục 1 GIAO KẾT HỢP ĐỒNG LAO ĐỘNG"]
    assert a17.content == frozen_article(frozen, "Dieu_17")
    a18 = next(c for c in r.chunks if c.doc_id == "Dieu_18")
    assert a18.title == "Điều 18. Thẩm quyền giao kết hợp đồng lao động"


def test_out_of_sequence_markers_stay_text_and_gaps_fail_validation(tmp_path):
    text = (ROOT / FIX / "labour_chuong1_dieu3_6.txt").read_text(encoding="utf-8")
    start = text.index("Điều 4.")
    end = text.index("Điều 5.")
    gap = tmp_path / "gap.txt"
    gap.write_text(text[:start] + text[end:], encoding="utf-8")  # real text with Điều 4 removed
    cfg = {"version": 1, "output": {"corpus": str(tmp_path / "gap.json"), "manifest": str(tmp_path / "gap.manifest.json")},
           "sources": [{"path": str(gap), "doc_code": "GAP", "ruleset": "vi_legal", "chunking": {"granularity": "article"}}]}
    cfg_path = tmp_path / "gap.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    result = build(cfg_path, ROOT)
    assert not result.ok and any("not contiguous" in e and "[4]" in e for e in result.errors)
    written, manifest_path = write_outputs(result, ROOT)
    assert written is None and not (tmp_path / "gap.json").exists()  # no corpus from a failed validation
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "failed"  # but the failure is preserved
    cfg["sources"][0]["ruleset_options"] = {"contiguous_articles": "warn"}
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    relaxed = build(cfg_path, ROOT)
    assert relaxed.ok and any("not contiguous" in w for w in relaxed.manifest["warnings"])


# ------------------------------------------------------------------------------------------ loaders

FORMAT_FILES = ["labour_chuong1_dieu1_2.md", "labour_chuong1_dieu1_2.html", "labour_chuong1_dieu1_2.docx"]


def generic_source(name):
    return {"path": f"{FIX}/{name}", "doc_code": "LAB", "collection_id": "labor_excerpt", "ruleset": "generic_headings",
            "ruleset_options": {"heading_styles": ["markdown"]}, "chunking": {"granularity": 3}}


@pytest.mark.parametrize("name", FORMAT_FILES)
def test_markdown_html_docx_loaders_produce_the_same_articles(tmp_path, frozen, name):
    r = run_config(tmp_path, [generic_source(name)])
    assert r.ok, r.errors
    articles = [c for c in r.chunks if c.title.startswith("Điều")]
    assert [c.title for c in articles] == ["Điều 1. Phạm vi điều chỉnh", "Điều 2. Đối tượng áp dụng"]
    for c in articles:
        assert c.source_pages == []
        assert c.section_path == ["Bộ luật Lao động 2019 (trích Chương I)", "Chương I. NHỮNG QUY ĐỊNH CHUNG"]
        body = fold(c.content.replace("### ", "", 1))
        num = "Dieu_" + c.title.split()[1].rstrip(".")
        assert body == frozen_article(frozen, num)  # verbatim legal text survives every format
    assert [c.doc_id for c in articles] == ["LAB_S1_1_1", "LAB_S1_1_2"]
    assert r.manifest["sources"][0]["format"] == name.rsplit(".", 1)[1].replace("md", "markdown")
    assert "KHÔNG PHẢI NỘI DUNG" not in json.dumps(r.records, ensure_ascii=False)
    assert "color" not in json.dumps(r.records)


def test_docx_table_is_flattened_and_reported(tmp_path):
    r = run_config(tmp_path, [generic_source("labour_chuong1_dieu1_2.docx")])
    lead = next(c for c in r.chunks if c.doc_id.endswith("_lead"))
    assert "Điều 2 | Đối tượng áp dụng" in lead.content
    src = r.manifest["sources"][0]
    assert src["loader"]["info"]["tables"] == 1
    assert any("table(s) flattened" in w for w in src["validation"]["warnings"])


def test_html_entities_and_charset_are_decoded(tmp_path):
    r = loaders.load_document(ROOT / FIX / "labour_chuong1_dieu1_2.html", "html", {})
    text = r.pages[0].text
    assert "Điều 1. Phạm vi điều chỉnh" in text and "Bộ luật Lao động quy định tiêu chuẩn lao động" in text
    assert r.info["html_title"] == "Bộ luật Lao động 2019 (trích)"


def test_pdf_loader_pages_and_running_header_audit():
    loaded = loaders.load_document(GAZETTE, "pdf", {})
    assert len(loaded.pages) == 94 and [p.number for p in loaded.pages][:3] == [1, 2, 3]
    norm = normalize(loaded, NormalizeConfig())
    assert "CÔNG BÁO/Số" not in norm.text and "ng ười" not in norm.text  # header gone, word spacing intact
    assert norm.pages_for(0, 10) == [1]
    assert {r["shape"] for r in norm.removed} == {"CÔNG BÁO/Số # + #/Ngày #-#-# #", "# CÔNG BÁO/Số # + #/Ngày #-#-#"}
    off = normalize(loaded, NormalizeConfig(remove_repeated_edges=False, strip_page_numbers=False))
    assert off.removed == [] and off.text.count("CÔNG BÁO/Số") == 93  # opt-out keeps every header line


def test_normalization_only_touches_formatting():
    # real sentence from Điều 1 of the Labour Code, with a soft-hyphen line break inside a word, a no-break space,
    # a zero-width space and decomposed (NFD) diacritics as an extractor could emit them
    import unicodedata
    sentence = "Bộ luật Lao động quy định tiêu chuẩn lao động; quyền, nghĩa vụ, trách nhiệm của người lao động"
    noisy = sentence.replace("tiêu chuẩn", "tiêu chu\u00ad\nẩn").replace("quyền,", "quyền,\u00a0")
    noisy = unicodedata.normalize("NFD", noisy.replace("nghĩa vụ", "nghĩa\u200b vụ"))
    assert "\u00ad\n" in noisy and noisy != sentence
    doc = loaders.LoadedDocument("text", [loaders.LoadedPage(None, noisy)])
    norm = normalize(doc, NormalizeConfig())
    assert " ".join(norm.text.split()) == " ".join(unicodedata.normalize("NFC", sentence).split())
    assert unicodedata.is_normalized("NFC", norm.text)
    # ASCII hyphen joins are opt-in because a trailing "-" can be a real compound or a date range
    hyph = loaders.LoadedDocument("text", [loaders.LoadedPage(None, "quan hệ lao-\nđộng\nngày 26-12-2019")])
    assert normalize(hyph, NormalizeConfig()).text == "quan hệ lao-\nđộng\nngày 26-12-2019"
    assert normalize(hyph, NormalizeConfig(join_hyphenated=True)).text == "quan hệ laođộng\nngày 26-12-2019"


def test_pdf_without_text_layer_is_an_error_not_an_empty_corpus(tmp_path):
    from pypdf import PdfWriter
    blank = tmp_path / "scan_like.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with blank.open("wb") as fh:
        writer.write(fh)
    with pytest.raises(NoTextLayerError, match="OCR is not implemented"):
        loaders.load_document(blank, "pdf", {})


def test_missing_optional_library_names_the_package():
    with pytest.raises(MissingDependencyError, match="python-docx") as exc:
        loaders._require("definitely_not_an_installed_package_xyz", "DOCX ingestion", "python-docx")
    assert exc.value.package == "definitely_not_an_installed_package_xyz"


def test_bad_configuration_is_rejected_with_clear_errors(tmp_path):
    base = {"path": f"{FIX}/labour_dieu17_18.txt", "ruleset": "vi_legal", "chunking": {"granularity": "article"}}
    with pytest.raises(ConfigError, match="unknown ruleset"):
        run_config(tmp_path, [{**base, "ruleset": "no_such_ruleset"}])
    with pytest.raises(ConfigError, match="unknown key"):
        run_config(tmp_path, [{**base, "colour": "red"}])
    with pytest.raises(ConfigError, match="granularity 'banana'"):
        run_config(tmp_path, [{**base, "chunking": {"granularity": "banana"}}])
    with pytest.raises(ConfigError, match="unknown option"):
        run_config(tmp_path, [{**base, "ruleset_options": {"nope": 1}}])
    with pytest.raises(IngestionError, match="not found"):
        run_config(tmp_path, [{**base, "path": f"{FIX}/missing.txt"}])
    with pytest.raises(IngestionError, match="no structure"):
        run_config(tmp_path, [{"path": f"{FIX}/labour_dieu17_18.txt", "ruleset": "generic_headings",
                               "chunking": {"granularity": 1}}])
    fallback = run_config(tmp_path, [{"path": f"{FIX}/labour_dieu17_18.txt", "ruleset": "generic_headings",
                                      "chunking": {"granularity": 1, "on_no_structure": "document"}}])
    assert fallback.ok and [c.level for c in fallback.chunks] == ["document"]
    assert fallback.manifest["sources"][0]["fallback_chunking"] == "document"  # the fallback is recorded, never silent


# ------------------------------------------------------------------------------- paragraph ruleset

def test_paragraph_ruleset_respects_size_and_overlap(tmp_path):
    src = {"path": f"{FIX}/labour_chuong1_dieu3_6.txt", "doc_code": "P", "ruleset": "paragraph",
           "ruleset_options": {"max_chars": 600, "overlap_chars": 150}, "chunking": {}}
    r = run_config(tmp_path, [src])
    assert r.ok, r.errors
    assert all(len(c.content) <= 600 for c in r.chunks) and len(r.chunks) > 5
    assert all(r.chunks[i + 1].char_start < r.chunks[i].char_end for i in range(len(r.chunks) - 1))  # consecutive chunks overlap
    assert all(r.chunks[i + 1].char_start > r.chunks[i].char_start for i in range(len(r.chunks) - 1))
    assert r.manifest["sources"][0]["validation"]["coverage"]["non_whitespace_fraction"] == 1.0
    assert len({c.doc_id for c in r.chunks}) == len(r.chunks) and r.chunks[0].doc_id == "P_P0001"
    # an oversize paragraph is cut at sentence or whitespace boundaries, never mid-word
    long_para = run_config(tmp_path, [{**src, "ruleset_options": {"max_chars": 80, "overlap_chars": 0}}])
    assert long_para.ok and all(len(c.content) <= 80 for c in long_para.chunks)
    assert all(c.content == c.content.strip() for c in long_para.chunks)


# --------------------------------------------------------------------------- extensibility

def test_new_domain_ruleset_can_be_registered():
    @register_ruleset
    class NumberedFaqRuleset(GenericHeadingsRuleset):
        name = "test_numbered_faq"
        defaults = {**GenericHeadingsRuleset.defaults, "heading_styles": ["decimal"]}
        default_chunking = {**GenericHeadingsRuleset.default_chunking, "granularity": 1}

    try:
        rs = rulesets.get_ruleset("test_numbered_faq")
        text = "1. Phạm vi\nNội dung một.\n2. Đối tượng\nNội dung hai."
        result = rs.parse(text, "doc")
        assert [n.label for n in result.nodes] == ["1. Phạm vi", "2. Đối tượng"]
    finally:
        rulesets.RULESETS.pop("test_numbered_faq", None)


# ------------------------------------------------------------------------------------- HCMUT config

@pytest.mark.skipif(not HCMUT_CFG.exists() or not (ROOT / "docs/materials/hcmut-sources/manifest.json").exists(),
                    reason="HCMUT sources/config not present")
def test_hcmut_config_builds_with_provenance_from_the_collection_manifest():
    r = build(HCMUT_CFG, ROOT)
    assert r.ok, r.errors[:5]
    collection = json.loads((ROOT / "docs/materials/hcmut-sources/manifest.json").read_text(encoding="utf-8"))["documents"]
    included = [d for d in collection if d.get("included_in_corpus")]
    assert len(r.manifest["sources"]) == len(included)
    ids = [c.doc_id for c in r.chunks]
    assert len(ids) == len(set(ids)) and all(i.startswith("HCMUT_") for i in ids)
    assert {"HCMUT_NOIQUY1924_QD_Dieu_1", "HCMUT_NOIQUY1924_Dieu_1"} <= set(ids)  # decision wrapper vs attached regulation
    by_code = {d["doc_code"]: d for d in included}
    for src in r.manifest["sources"]:
        d = by_code[src["doc_code"]]
        assert src["sha256"] == d["sha256"] == sha256_file(ROOT / src["path"])
        assert src["document_number"] == d["document_number"] and src["url"] == d["source_url"]
    sample = next(c for c in r.chunks if c.doc_id == "HCMUT_NOIQUY1924_Dieu_1")
    assert sample.extra["metadata_verification"] == by_code["NOIQUY1924"]["metadata_verification"]
    assert sample.source_pages and sample.issued_date == by_code["NOIQUY1924"]["issued_date"]
    assert Counter(c.level for c in r.chunks)["article"] > 50
    assert r.corpus_text == build(HCMUT_CFG, ROOT).corpus_text


@pytest.mark.skipif(not HCMUT_CFG.exists(), reason="HCMUT config not present")
def test_provenance_is_never_attached_to_a_different_file(tmp_path):
    cfg = yaml.safe_load(HCMUT_CFG.read_text(encoding="utf-8"))
    cfg["output"] = {"corpus": str(tmp_path / "h.json"), "manifest": str(tmp_path / "h.manifest.json")}
    first, second = cfg["sources"][0], cfg["sources"][1]
    first["path"] = second["path"]  # HVDT1260 metadata + HVDT2749 PDF
    cfg["sources"] = [first]
    p = tmp_path / "h.yaml"
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    with pytest.raises(IngestionError, match="sha256"):
        build(p, ROOT)
