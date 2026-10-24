"""L1 v2 verifier: real corpus records, real profiles, the real v1 verifier, real recorded ledgers. No mocks.

Checks mechanics of a lexical verifier (what passes or fails, and what the repair feedback says). A pass is a lexical
proxy, never a statement that an answer is correct.
"""
import json
import re
from pathlib import Path

import pytest

from src.agent.citations import parse_model_citations
from src.agent.state import Citation
from src.config.app_config import AppConfig, load_config
from src.domains import load_profile
from src.pipeline import Overrides, build_components
from src.verifier.lexical_grounding import LexicalGroundingVerifier
from src.verifier.lexical_grounding_v2 import (LexicalGroundingVerifierV2, check_quote, fold, make_lexical_verifier,
                                               source_units)
from src.verifier.pipeline import VerificationPipeline

ROOT = Path(__file__).resolve().parents[1]
HCMUT_CORPUS = json.loads((ROOT / "data/corpus/hcmut_academic_v1.json").read_text(encoding="utf-8"))
LABOUR_CORPUS = json.loads((ROOT / "data/corpus/labour_vi_v1.json").read_text(encoding="utf-8"))
HCMUT = {r["doc_id"]: r for r in HCMUT_CORPUS}
LABOUR = {r["doc_id"]: r for r in LABOUR_CORPUS}

CREDIT_RECORD = "HCMUT_HVDT1260_Dieu_1_S5_3"        # "17 tín\nchỉ" (unit split by a line break), 11/25 tín chỉ ...
DURATION_RECORD = "HCMUT_HVDT1260_Dieu_1_S3_1"      # table of training durations
PERMIT_RECORD = "ND219_2025_Dieu_22"                # "60 ngày" (filing) and "10 ngày làm việc" (decision) in one record
MATERNITY_RECORD = "BLLD2019_Dieu_139"


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@pytest.fixture(scope="module")
def hcmut_v2():
    return LexicalGroundingVerifierV2(HCMUT_CORPUS, profile=load_profile("hcmut_academic"))


@pytest.fixture(scope="module")
def hcmut_v1():
    return LexicalGroundingVerifier(HCMUT_CORPUS, profile=load_profile("hcmut_academic"))


@pytest.fixture(scope="module")
def labour_v2():
    return LexicalGroundingVerifierV2(LABOUR_CORPUS, profile=load_profile("labour_vi_multi"))


@pytest.fixture(scope="module")
def labour_v1():
    return LexicalGroundingVerifier(LABOUR_CORPUS, profile=load_profile("labour_vi_multi"))


def record_text(corpus: dict, doc_id: str) -> str:
    return fold(corpus[doc_id]["content"])


def cite(doc_id: str, quote: str = None) -> list:
    return [Citation(article_id=doc_id, exact_quote=quote)]


# --- 1. exact quote -----------------------------------------------------------------------------------------------

FIRST = "Thời gian đào tạo chuẩn, kế hoạch và tối đa tính theo số học kỳ chính được quy định"
LAST = "Số học kỳ giảm = [Số học kỳ đào tạo chuẩn] x [Số tín chỉ miễn trừ] / [Số tín chỉ toàn khoá]"


def test_quote_fragments_used_below_are_verbatim_in_the_real_record():
    text = HCMUT[DURATION_RECORD]["content"]
    assert squash(FIRST) in squash(text) and squash(LAST) in squash(text)


@pytest.mark.parametrize("ellipsis", ["...", "…", "[...]", "[…]", "(...)", " ... "])
def test_quote_with_elision_passes_when_segments_are_verbatim_and_in_order(hcmut_v1, hcmut_v2, ellipsis):
    quote = f"{FIRST} {ellipsis} {LAST}"
    assert check_quote(quote, record_text(HCMUT, DURATION_RECORD)).ok
    citations = cite(DURATION_RECORD, quote)
    answer = "Thời gian đào tạo chuẩn, kế hoạch và tối đa tính theo số học kỳ chính được quy định trong văn bản."
    assert hcmut_v2.verify(answer, citations, [DURATION_RECORD]).is_valid
    assert not hcmut_v1.verify(answer, citations, [DURATION_RECORD]).is_valid     # v1 rejects every elided quote


def test_quote_with_segments_out_of_order_or_altered_fails():
    record = record_text(HCMUT, DURATION_RECORD)
    assert not check_quote(f"{LAST} ... {FIRST}", record).ok
    altered = LAST.replace("toàn khoá", "toàn bộ khoá")
    result = check_quote(f"{FIRST} ... {altered}", record)
    assert not result.ok and result.failing and "toàn bộ" in result.failing


@pytest.mark.parametrize("wrap", ['"{}"', "“{}”", "'{}'", "({})", "[{}]", "«{}»", "{}.", "“{}.”", " **{}** "])
def test_wrapper_characters_and_whitespace_do_not_break_a_verbatim_quote(wrap):
    quote = wrap.format("Thời gian đào tạo chuẩn,   kế hoạch\nvà tối đa tính theo số học kỳ chính")
    assert check_quote(quote, record_text(HCMUT, DURATION_RECORD)).ok


def test_case_and_unicode_form_are_normalised_but_wording_is_not():
    import unicodedata
    record = record_text(HCMUT, DURATION_RECORD)
    quote = "THỜI GIAN ĐÀO TẠO CHUẨN, KẾ HOẠCH VÀ TỐI ĐA"
    assert check_quote(unicodedata.normalize("NFD", quote), record).ok
    assert not check_quote("Thời gian học chuẩn, kế hoạch và tối đa", record).ok


def test_a_paraphrase_still_fails_and_the_feedback_shows_the_source(hcmut_v2):
    paraphrase = "Sinh viên chính quy có thể học tối đa 12 học kỳ chính theo quy định về thời gian đào tạo."
    result = hcmut_v2.verify("Thời gian đào tạo tối đa của sinh viên chính quy là 12 học kỳ chính.",
                             cite(DURATION_RECORD, paraphrase), [DURATION_RECORD])
    assert not result.is_valid and result.invalid_citations
    assert "không khớp nguyên văn" in result.repair_feedback and DURATION_RECORD in result.repair_feedback
    span = re.search(r"«(.*?)»", result.repair_feedback, re.S).group(1).strip("… ")
    assert squash(span) in squash(HCMUT[DURATION_RECORD]["content"])      # verbatim source text, ready to copy


def test_numbers_inside_a_quote_must_match_exactly():
    record = record_text(HCMUT, CREDIT_RECORD)
    assert check_quote("Sinh viên chính quy: 25 tín chỉ", record).ok
    assert not check_quote("Sinh viên chính quy: 24 tín chỉ", record).ok
    assert check_quote("của hình thức chính quy là 17 tín chỉ", record).ok          # unit split by a line break
    assert not check_quote("7 tín chỉ và của hình thức vừa làm vừa học", record).ok   # '7' is the tail of '17'
    # a number in a short skipped segment between two long ones must still exist in the record
    first, last = "Số tín chỉ tối thiểu của sinh viên trong một học kỳ chính", "Sinh viên chính quy: 25 tín chỉ"
    assert check_quote(f"{first} ... 28 ... {last}", record).ok
    assert not check_quote(f"{first} ... 29 ... {last}", record).ok


def test_list_numbering_dropped_from_a_quote_is_tolerated_but_content_is_not():
    record = record_text(LABOUR, "ND318_2025_Dieu_8")
    assert "2. dữ liệu được thu thập" in record
    assert check_quote("Cơ sở dữ liệu về người lao động bao gồm các thông tin quy định tại Điều 4 Nghị định này. "
                       "Dữ liệu được thu thập, cập nhật, đồng bộ vào cơ sở dữ liệu", record).ok
    assert not check_quote("Cơ sở dữ liệu về người lao động bao gồm các thông tin quy định tại Điều 5 Nghị định này. "
                           "Dữ liệu được thu thập", record).ok


def test_the_quote_must_come_from_the_cited_record(hcmut_v2):
    quote = "Số tín chỉ tối thiểu của sinh viên trong một học kỳ chính như sau"
    ok = hcmut_v2.analyze("Sinh viên chính quy học tối thiểu 11 tín chỉ.", cite(CREDIT_RECORD, quote), [CREDIT_RECORD])
    assert ok.passed
    wrong = hcmut_v2.analyze("Sinh viên chính quy học tối thiểu 11 tín chỉ.", cite(DURATION_RECORD, quote),
                             [CREDIT_RECORD, DURATION_RECORD])
    kinds = {f.kind: f for f in wrong.findings}
    assert "quote_mismatch" in kinds
    assert kinds["quote_mismatch"].detail["other_record"] == CREDIT_RECORD       # the hint names the right record
    assert CREDIT_RECORD in kinds["quote_mismatch"].message


# --- 2. claim-local quantities -------------------------------------------------------------------------------------

DECISION = "Cơ quan có thẩm quyền xem xét và cấp giấy phép lao động cho người lao động nước ngoài trong thời hạn {} kể từ ngày nhận đủ hồ sơ đề nghị."


def test_a_wrong_number_printed_elsewhere_in_the_record_fails_in_v2_but_passes_in_v1(labour_v1, labour_v2):
    """LVN-017 pattern: the record prints '60 ngày' in the filing clause and '10 ngày' in the decision clause."""
    assert "60 ngày" in LABOUR[PERMIT_RECORD]["content"] and "10 ngày làm việc" in LABOUR[PERMIT_RECORD]["content"]
    right, wrong = DECISION.format("10 ngày làm việc"), DECISION.format("60 ngày làm việc")
    citations, retrieved = cite(PERMIT_RECORD), [PERMIT_RECORD]
    assert labour_v1.verify(wrong, citations, retrieved).is_valid          # document-level check: the number exists
    assert labour_v2.verify(right, citations, retrieved).is_valid
    report = labour_v2.analyze(wrong, citations, retrieved)
    assert report.reasons == ["quantity_not_local"]
    result = labour_v2.verify(wrong, citations, retrieved)
    assert not result.is_valid and "60 ngày" in result.repair_feedback and "10 ngày làm việc" in result.repair_feedback
    assert result.unsupported_claims == [wrong]


def test_the_same_number_passes_in_the_clause_it_belongs_to(labour_v2):
    sentence = "Người sử dụng lao động nộp hồ sơ đề nghị cấp giấy phép lao động trong thời hạn 60 ngày nhưng không ít hơn 10 ngày tính đến ngày người lao động nước ngoài dự kiến làm việc."
    assert labour_v2.verify(sentence, cite(PERMIT_RECORD), [PERMIT_RECORD]).is_valid


def test_a_number_that_is_nowhere_in_the_record_is_reported_as_absent(labour_v2):
    report = labour_v2.analyze(DECISION.format("99 ngày làm việc"), cite(PERMIT_RECORD), [PERMIT_RECORD])
    assert report.reasons == ["quantity_absent"]


def test_decimal_comma_and_dot_are_the_same_quantity_and_a_unit_may_span_a_line_break(hcmut_v2):
    from src.verifier.lexical_grounding import _quantity_key
    assert _quantity_key("3,5 tháng") == _quantity_key("3.5 tháng") == "3.5:tháng"
    assert _quantity_key("17 tín\nchỉ") == _quantity_key("17 tín chỉ")
    assert hcmut_v2.verify("Số tín chỉ thiết kế trung bình cho một học kỳ chính của hình thức chính quy là 17 tín chỉ.",
                           cite(CREDIT_RECORD), [CREDIT_RECORD]).is_valid
    assert not hcmut_v2.verify("Số tín chỉ thiết kế trung bình cho một học kỳ chính của hình thức chính quy là 97 tín chỉ.",
                               cite(CREDIT_RECORD), [CREDIT_RECORD]).is_valid


# --- 3. claim support ----------------------------------------------------------------------------------------------

def test_a_faithful_sentence_passes_and_an_unrelated_one_fails_with_the_closest_source_span(hcmut_v2):
    faithful = "Sinh viên vừa làm vừa học và đào tạo từ xa được đăng ký tối thiểu 09 tín chỉ trong một học kỳ chính."
    assert hcmut_v2.verify(faithful, cite(CREDIT_RECORD), [CREDIT_RECORD]).is_valid
    invented = "Sinh viên được miễn toàn bộ học phí nếu tham gia hoạt động tình nguyện của nhà trường."
    result = hcmut_v2.verify(invented, cite(CREDIT_RECORD), [CREDIT_RECORD])
    assert not result.is_valid and result.unsupported_claims == [invented]
    assert CREDIT_RECORD in result.repair_feedback
    span = re.search(r"«[^»]*»[^«]*«(.*?)»", result.repair_feedback, re.S).group(1).strip("… ")
    assert squash(span) in squash(HCMUT[CREDIT_RECORD]["content"])


def test_sentence_coverage_is_reported_per_sentence_against_the_best_window(hcmut_v2):
    answer = ("Sinh viên chính quy được học tối đa 25 tín chỉ trong một học kỳ chính. "
              "Sinh viên được miễn toàn bộ học phí nếu tham gia hoạt động tình nguyện của nhà trường.")
    report = hcmut_v2.analyze(answer, cite(CREDIT_RECORD), [CREDIT_RECORD])
    coverage = [s["coverage"] for s in report.sentences]
    assert len(coverage) == 2 and coverage[0] > hcmut_v2.support_threshold > coverage[1]
    assert report.reasons == ["claim_unsupported"] and report.findings[0].sentence.startswith("Sinh viên được miễn")


def test_a_list_item_is_read_together_with_its_lead_in(hcmut_v2):
    """'tối thiểu ... học kỳ chính' is in the sentence that introduces the list, the 09 tín chỉ is two items further."""
    sentence = "Sinh viên vừa làm vừa học và đào tạo từ xa được đăng ký tối thiểu 09 tín chỉ trong một học kỳ chính."
    assert hcmut_v2.verify(sentence, cite(CREDIT_RECORD), [CREDIT_RECORD]).is_valid
    wrong = sentence.replace("09 tín chỉ", "19 tín chỉ")        # 19 is the *maximum* for the same group: a different clause
    assert hcmut_v2.analyze(wrong, cite(CREDIT_RECORD), [CREDIT_RECORD]).reasons == ["quantity_not_local"]


def test_a_lead_in_line_is_not_scored(hcmut_v2):
    answer = "Dựa trên các văn bản tra cứu:\nSinh viên chính quy được học tối đa 25 tín chỉ trong một học kỳ chính."
    assert hcmut_v2.verify(answer, cite(CREDIT_RECORD), [CREDIT_RECORD]).is_valid


def test_source_units_join_soft_wraps_and_keep_list_items_apart():
    units = source_units(HCMUT[CREDIT_RECORD]["content"])
    assert any("là 17 tín chỉ và của hình thức" in u for u in units)          # 'tín\nchỉ' re-joined
    assert any(u.startswith("- Sinh viên chính quy: 25 tín chỉ") for u in units)
    assert all(len(u) <= 400 for u in units)


# --- other L1 stages, feedback budget, pipeline ----------------------------------------------------------------------

def test_existence_provenance_empty_and_missing_citation_still_reject(hcmut_v2):
    answer = "Sinh viên chính quy học tối đa 25 tín chỉ."
    assert hcmut_v2.analyze(answer, cite("HCMUT_KHONG_TON_TAI"), [CREDIT_RECORD]).reasons == ["unknown_citation"]
    assert hcmut_v2.analyze(answer, cite(CREDIT_RECORD), []).reasons == ["unretrieved_citation"]
    assert hcmut_v2.analyze("", cite(CREDIT_RECORD), [CREDIT_RECORD]).reasons == ["empty_answer"]
    assert hcmut_v2.analyze(answer, [], [CREDIT_RECORD]).reasons == ["missing_citation"]
    assert hcmut_v2.verify(answer, [], [CREDIT_RECORD]).invalid_citations == ["MISSING_CITATION"]


def test_citation_and_sentence_problems_are_reported_together_and_the_feedback_is_short(hcmut_v2):
    answer = ("Sinh viên chính quy học tối đa 99 tín chỉ. Sinh viên được miễn toàn bộ học phí nếu tham gia hoạt động tình nguyện. "
              "Mọi sinh viên đều phải đóng thêm lệ phí ký túc xá hằng tháng theo mức do nhà trường quy định.")
    result = hcmut_v2.verify(answer, cite(CREDIT_RECORD, "Sinh viên chính quy: 24 tín chỉ"), [CREDIT_RECORD])
    reasons = hcmut_v2.analyze(answer, cite(CREDIT_RECORD, "Sinh viên chính quy: 24 tín chỉ"), [CREDIT_RECORD]).reasons
    assert reasons[0] == "quote_mismatch" and len(reasons) >= 3
    assert result.repair_feedback.count("\n") == 1                         # at most two findings
    assert len(result.repair_feedback) < 1000


def test_v2_works_inside_the_verification_pipeline(hcmut_v2):
    pipeline = VerificationPipeline(lexical_verifier=hcmut_v2, mode="l1")
    good = pipeline.verify("Sinh viên chính quy học tối đa 25 tín chỉ trong một học kỳ chính.", cite(CREDIT_RECORD),
                           [CREDIT_RECORD])
    assert good.is_valid and good.repair_feedback is None
    bad = pipeline.verify("Sinh viên chính quy học tối đa 35 tín chỉ trong một học kỳ chính.", cite(CREDIT_RECORD),
                          [CREDIT_RECORD])
    assert not bad.is_valid and "35 tín chỉ" in bad.repair_feedback


def test_profile_messages_for_v2_come_from_the_language_pack():
    for name in ("labour_vi_2019", "labour_vi_multi", "hcmut_academic"):
        messages = load_profile(name).messages
        assert "{span}" in messages.l1v2_claim and "{span}" in messages.l1v2_quantity and "{span}" in messages.l1v2_quote_mismatch
        assert messages.l1v2_quote_other_record.format(doc_id="A", other_id="B").count("'B'") == 2


# --- 5. switch ---------------------------------------------------------------------------------------------------------

def test_support_threshold_default_is_the_code_default_and_zero_switches_the_sentence_check_off(hcmut_v2):
    from src.verifier.lexical_grounding_v2 import DEFAULT_SUPPORT_THRESHOLD
    assert AppConfig().verifier.l1_support_threshold == DEFAULT_SUPPORT_THRESHOLD == hcmut_v2.support_threshold
    invented = "Sinh viên được miễn toàn bộ học phí nếu tham gia hoạt động tình nguyện của nhà trường."
    assert not hcmut_v2.verify(invented, cite(CREDIT_RECORD), [CREDIT_RECORD]).is_valid
    off = LexicalGroundingVerifierV2(HCMUT_CORPUS, profile=load_profile("hcmut_academic"), support_threshold=0.0)
    assert off.verify(invented, cite(CREDIT_RECORD), [CREDIT_RECORD]).is_valid
    assert not off.verify("Sinh viên chính quy học tối đa 35 tín chỉ.", cite(CREDIT_RECORD), [CREDIT_RECORD]).is_valid


def test_l1_version_switch_in_config_and_builder(tmp_path):
    assert AppConfig().verifier.l1_version == "v1"   # default keeps existing configs (frozen v3) meaning the same
    assert AppConfig(verifier={"l1_version": "v2"}).verifier.l1_version == "v2"
    assert AppConfig(verifier={"l1_version": "v1"}).verifier.l1_version == "v1"
    with pytest.raises(Exception, match="l1_version"):
        AppConfig(verifier={"l1_version": "v3"})
    with pytest.raises(ValueError, match="l1_version"):
        make_lexical_verifier([], "v3")
    base = load_config(str(ROOT / "config/config.yaml"))
    for version, cls in (("v2", LexicalGroundingVerifierV2), ("v1", LexicalGroundingVerifier)):
        cfg = base.model_copy(deep=True)
        cfg.verifier.l1_version = version
        cfg.memory.sqlite_path = str(tmp_path / f"{version}.db")
        cfg.security.audit_log_path = str(tmp_path / f"{version}.audit.jsonl")
        cfg.security.outbox_path = str(tmp_path / f"{version}.outbox.jsonl")
        parts = build_components(cfg)
        assert type(parts.lexical_verifier) is cls
        assert parts.verification_pipeline.lexical_verifier is parts.lexical_verifier


# --- 8. v1 is unchanged: replay of the frozen D2 v3 ledgers ---------------------------------------------------------

@pytest.mark.parametrize("run_name, corpus_path, profile_name", [
    ("d2-gpu-main-hcmut-v3", "data/corpus/hcmut_academic_v1.json", "hcmut_academic"),
    ("d2-gpu-main-labour-v3", "data/corpus/labour_vi_v1.json", "labour_vi_multi")])
def test_v1_reproduces_every_recorded_l1_decision_of_the_frozen_runs(run_name, corpus_path, profile_name):
    """Each answer draft of the L1 / L1+rerank trials was verified by the v1 verifier during the run; the repair
    feedback, the acceptance, or the refusal text it produced is in the ledger. v1 must reproduce all of them."""
    trials_path = ROOT / "evaluation/runs" / run_name / "trials.jsonl"
    assert trials_path.is_file(), f"frozen run artifact missing: {trials_path}"
    manifest = json.loads((trials_path.parent / "manifest.json").read_text(encoding="utf-8"))
    profile = load_profile(manifest["benchmarks"][0]["profile"])
    assert profile.id == load_profile(profile_name).id
    verifier = make_lexical_verifier(json.loads((ROOT / corpus_path).read_text(encoding="utf-8")), "v1", profile=profile)
    checked = {"repair": 0, "accepted": 0, "refused": 0}
    for line in trials_path.read_text(encoding="utf-8").splitlines():
        trial = json.loads(line)
        if trial["variant"] not in ("l1", "l1_rerank"):
            continue
        ledger = trial["ledger"]
        repairs = [e["feedback"] for e in ledger["audit_events"] if e.get("event") == "repair"]
        drafts = [c["response"]["tool_args"] for c in ledger["llm_calls"]
                  if isinstance(c.get("response"), dict) and c["response"].get("action") == "answer"]
        final = ledger["final_output"]
        for i, draft in enumerate(drafts):
            result = verifier.verify(draft.get("content", ""), parse_model_citations(profile, draft.get("citations", [])),
                                     ledger["retrieved_article_ids"])
            if i < len(repairs):
                assert not result.is_valid and result.repair_feedback == repairs[i]
                checked["repair"] += 1
            elif final.get("action") == "answer":
                assert result.is_valid
                checked["accepted"] += 1
            else:
                assert not result.is_valid and result.repair_feedback in final["reason"]
                checked["refused"] += 1
    assert checked["repair"] > 50 and checked["accepted"] > 20, checked


def test_v1_module_text_is_the_frozen_original():
    """lexical_grounding.py (v1) is not edited by the v2 work: pinned by the digest it had at commit 0bc3108, the code
    the frozen D2 v3 runs were collected with. A deliberate change to v1 must update this digest and be called out."""
    import hashlib
    digest = hashlib.sha256((ROOT / "src/verifier/lexical_grounding.py").read_bytes()).hexdigest()
    assert digest == "97fa895743da4658065193febe14f330d77488312427e6bfd3b37e7b03ef3ee5"
