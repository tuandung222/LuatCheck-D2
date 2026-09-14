"""
Automated Error Diagnostic Analyzer for LuatCheck Benchmark
Phân loại lỗi định lượng tự động theo 6 failure modes chuẩn hóa:
1. retrieval_miss: Gold provision not in retrieved top-k
2. wrong_provision_cited: Cited article is not in ground-truth article set
3. unsupported_claim: Generated claim sentence is unsupported by cited text
4. over_refusal: Refused on an answerable task
5. budget_exhausted: Exceeded 5 tool calls or 2 repairs
6. parse_error: Structured parse/JSON validation failure
"""
import json
import os
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Set


def normalize_id(aid: str) -> str:
    """Chuẩn hóa mã điều luật: Dieu_25, dieu_25, Điều 25 -> dieu_25"""
    if not aid:
        return ""
    norm = unicodedata.normalize("NFC", str(aid).strip().lower())
    norm = norm.replace(" ", "_")
    if norm.startswith("điều_") or norm.startswith("điều_"):
        norm = "dieu_" + norm[5:]
    elif norm.startswith("điều") or norm.startswith("điều"):
        norm = "dieu_" + norm[4:].lstrip("_")
    return norm


@dataclass
class CaseStudy:
    task_id: str
    query: str
    failure_mode: str
    what_failed: str
    why: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ErrorDiagnosticAnalyzer:
    """
    Automated Error Diagnostic Analyzer for LuatCheck Benchmark
    Chẩn đoán định lượng và phân tích ca thất bại (case studies)
    """
    FAILURE_MODES = [
        "retrieval_miss",
        "wrong_provision_cited",
        "unsupported_claim",
        "over_refusal",
        "budget_exhausted",
        "parse_error"
    ]

    FAILURE_DESCRIPTIONS = {
        "retrieval_miss": "Gold provision not in retrieved top-k",
        "wrong_provision_cited": "Cited article is not in ground-truth article set",
        "unsupported_claim": "Generated claim sentence is unsupported by cited text",
        "over_refusal": "Refused on an answerable task",
        "budget_exhausted": "Exceeded 5 tool calls or 2 repairs",
        "parse_error": "Structured parse/JSON validation failure"
    }

    def __init__(self, name: str = "default"):
        self.name = name
        self.total_tasks_evaluated = 0
        self.case_studies: List[CaseStudy] = []
        self.task_diagnoses: List[Dict[str, Any]] = []

    def record_task_evaluation(
        self,
        task: Dict[str, Any],
        ledger: Any,
        citations: Optional[List[Any]] = None,
        unsupported_sentence_rate: float = 0.0,
        unsupported_claims: Optional[List[str]] = None,
        parse_error_detected: bool = False,
        parse_error_details: Optional[str] = None
    ) -> List[str]:
        """
        Phân tích 1 task đã được agent xử lý, nhận diện các failure modes xuất hiện.
        Trả về danh sách các failure modes phát hiện được trong task.
        """
        self.total_tasks_evaluated += 1
        detected_modes: List[str] = []

        task_id = task.get("task_id", f"TASK_{self.total_tasks_evaluated}")
        query = task.get("question", "")
        expected_behavior = task.get("expected_behavior", "answer")

        gt_raw = task.get("ground_truth_article_ids", [])
        if not gt_raw and task.get("ground_truth_article_id"):
            gt_raw = [task.get("ground_truth_article_id")]
        gt_ids = [normalize_id(x) for x in gt_raw if x]

        retrieved_raw = getattr(ledger, "retrieved_article_ids", []) if ledger else []
        retrieved_ids = [normalize_id(x) for x in retrieved_raw if x]

        terminal_status = getattr(ledger, "terminal_status", "") if ledger else ""
        is_answered = (terminal_status == "answered")

        tool_calls_count = getattr(ledger, "tool_calls_count", 0) if ledger else 0
        repairs_count = getattr(ledger, "repairs_count", 0) if ledger else 0

        # Trích xuất danh sách điều luật được trích dẫn
        cited_ids = []
        if citations:
            for c in citations:
                if isinstance(c, dict):
                    aid = c.get("article_id", "")
                elif hasattr(c, "article_id"):
                    aid = getattr(c, "article_id", "")
                else:
                    aid = str(c)
                if aid:
                    cited_ids.append(normalize_id(aid))

        # 1. retrieval_miss: Gold provision not in retrieved top-k
        if gt_ids:
            has_retrieval_hit = any(gt in retrieved_ids for gt in gt_ids)
            if not has_retrieval_hit:
                detected_modes.append("retrieval_miss")
                cs = CaseStudy(
                    task_id=task_id,
                    query=query,
                    failure_mode="retrieval_miss",
                    what_failed=f"Căn cứ pháp lý chuẩn {gt_ids} không xuất hiện trong top-k truy xuất ({retrieved_ids[:5]})",
                    why="Bộ truy xuất kết hợp (BM25/Dense) không xếp hạng đúng điều luật cần thiết vào danh sách quan sát của agent.",
                    details={"ground_truth": gt_ids, "retrieved": retrieved_ids}
                )
                self.case_studies.append(cs)

        # 2. wrong_provision_cited: Cited article is not in ground-truth article set
        if is_answered and cited_ids:
            if gt_ids:
                invalid_cits = [c for c in cited_ids if c not in gt_ids]
                if invalid_cits:
                    detected_modes.append("wrong_provision_cited")
                    cs = CaseStudy(
                        task_id=task_id,
                        query=query,
                        failure_mode="wrong_provision_cited",
                        what_failed=f"Trích dẫn sai điều luật: {invalid_cits} (kỳ vọng: {gt_ids})",
                        why="Agent đưa ra kết luận dựa trên điều luật không thuộc căn cứ chuẩn hoặc gán nhầm điều luật tương tự.",
                        details={"cited": cited_ids, "ground_truth": gt_ids, "invalid": invalid_cits}
                    )
                    self.case_studies.append(cs)
            else:
                # Query không có căn cứ (Unanswerable/Adversarial) nhưng vẫn bịa trích dẫn
                detected_modes.append("wrong_provision_cited")
                cs = CaseStudy(
                    task_id=task_id,
                    query=query,
                    failure_mode="wrong_provision_cited",
                    what_failed=f"Tự ý trích dẫn điều luật {cited_ids} cho câu hỏi ngoài phạm vi điều chỉnh",
                    why="Agent ảo tưởng căn cứ pháp luật cho câu hỏi không có căn cứ hoặc vi phạm thẩm quyền.",
                    details={"cited": cited_ids, "ground_truth": []}
                )
                self.case_studies.append(cs)

        # 3. unsupported_claim: Generated claim sentence is unsupported by cited text
        if is_answered:
            if expected_behavior == "refuse":
                detected_modes.append("unsupported_claim")
                cs = CaseStudy(
                    task_id=task_id,
                    query=query,
                    failure_mode="unsupported_claim",
                    what_failed="Đưa ra câu trả lời khẳng định cho câu hỏi yêu cầu từ chối (expected_behavior == 'refuse')",
                    why="Agent không nhận diện được giới hạn thẩm quyền hoặc tấn công injection, phát biểu mệnh đề không có căn cứ.",
                    details={"expected_behavior": expected_behavior, "terminal_status": terminal_status}
                )
                self.case_studies.append(cs)
            elif unsupported_sentence_rate > 0.0 or (unsupported_claims and len(unsupported_claims) > 0):
                detected_modes.append("unsupported_claim")
                claims_desc = unsupported_claims[:2] if unsupported_claims else [f"USR: {unsupported_sentence_rate:.1%}"]
                cs = CaseStudy(
                    task_id=task_id,
                    query=query,
                    failure_mode="unsupported_claim",
                    what_failed=f"Phát hiện phát biểu không được chứng minh (USR={unsupported_sentence_rate:.1%})",
                    why=f"Mệnh đề trong câu trả lời không vượt qua kiểm định overlap L1 hoặc entailment L2: {claims_desc}",
                    details={"unsupported_rate": unsupported_sentence_rate, "unsupported_claims": unsupported_claims or []}
                )
                self.case_studies.append(cs)

        # 4. over_refusal: Refused on an answerable task
        if expected_behavior == "answer" and not is_answered:
            detected_modes.append("over_refusal")
            cs = CaseStudy(
                task_id=task_id,
                query=query,
                failure_mode="over_refusal",
                what_failed=f"Hệ thống từ chối hoặc làm rõ ({terminal_status}) đối với câu hỏi hợp lệ có căn cứ",
                why="Cơ chế bảo vệ hoặc verifier quá khắt khe, hoặc hết ngân sách sửa chữa dẫn đến từ chối oan.",
                details={"expected_behavior": expected_behavior, "terminal_status": terminal_status}
            )
            self.case_studies.append(cs)

        # 5. budget_exhausted: Exceeded or reached 5 tool calls or 2 repairs
        max_tools = getattr(ledger, "max_tool_calls", 5) if ledger else 5
        max_rep = getattr(ledger, "max_repairs", 2) if ledger else 2
        is_budget_exhausted = (
            tool_calls_count >= max_tools or
            repairs_count >= max_rep or
            bool(ledger and getattr(ledger, "terminal_status", None) == "refused" and "ngân sách" in str(getattr(ledger, "final_output", "")).lower())
        )
        if is_budget_exhausted:
            detected_modes.append("budget_exhausted")
            cs = CaseStudy(
                task_id=task_id,
                query=query,
                failure_mode="budget_exhausted",
                what_failed=f"Chạm ngưỡng ngân sách kiểm soát: {tool_calls_count}/{max_tools} công cụ, {repairs_count}/{max_rep} sửa chữa",
                why="Vòng lặp ReAct lúng túng trong việc tìm căn cứ hoặc không sửa được lỗi xác thực trong số lượt cho phép.",
                details={"tool_calls": tool_calls_count, "repairs": repairs_count}
            )
            self.case_studies.append(cs)

        # 6. parse_error: Structured parse/JSON validation failure
        if parse_error_detected:
            detected_modes.append("parse_error")
            cs = CaseStudy(
                task_id=task_id,
                query=query,
                failure_mode="parse_error",
                what_failed=f"Lỗi cú pháp cấu trúc JSON: {parse_error_details or 'Invalid JSON format'}",
                why="Mô hình cục bộ sinh chuỗi JSON không hợp lệ hoặc thiếu các trường bắt buộc, kích hoạt bộ dự phòng.",
                details={"error": parse_error_details}
            )
            self.case_studies.append(cs)

        self.task_diagnoses.append({
            "task_id": task_id,
            "detected_modes": detected_modes,
            "is_answered": is_answered,
            "expected_behavior": expected_behavior
        })

        return detected_modes

    def get_statistics(self) -> Dict[str, Any]:
        """
        Tính toán số lượng (counts), tần suất tỷ lệ phần trăm (frequencies),
        và gom nhóm case studies theo từng failure mode.
        """
        counts = {m: 0 for m in self.FAILURE_MODES}
        for cs in self.case_studies:
            if cs.failure_mode in counts:
                counts[cs.failure_mode] += 1

        total = max(self.total_tasks_evaluated, 1)
        frequencies = {
            m: round((counts[m] / total) * 100.0, 2)
            for m in self.FAILURE_MODES
        }

        studies_by_mode = {m: [] for m in self.FAILURE_MODES}
        for cs in self.case_studies:
            studies_by_mode[cs.failure_mode].append(cs.to_dict())

        return {
            "configuration": self.name,
            "total_tasks_evaluated": self.total_tasks_evaluated,
            "total_failure_instances": len(self.case_studies),
            "counts": counts,
            "frequencies_percent": frequencies,
            "case_studies": studies_by_mode
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_statistics()

    def export_json(self, filepath: Optional[str] = None, indent: int = 2) -> str:
        """Xuất kết quả chẩn đoán lỗi sang chuỗi JSON và ghi ra file nếu có đường dẫn."""
        data = self.to_dict()
        json_str = json.dumps(data, ensure_ascii=False, indent=indent)
        if filepath:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    def to_markdown_table(self) -> str:
        """
        Sinh bảng Markdown báo cáo chẩn đoán lỗi chuyên nghiệp theo định dạng bài báo khoa học.
        """
        stats = self.get_statistics()
        counts = stats["counts"]
        freqs = stats["frequencies_percent"]
        studies = stats["case_studies"]

        lines = []
        lines.append(f"### Error Diagnostic Taxonomy — `{self.name.upper()}`")
        lines.append(f"**Total Tasks Evaluated**: {self.total_tasks_evaluated} | **Total Failure Instances**: {len(self.case_studies)}\n")
        lines.append("| Failure Mode | Description | Count | Frequency (%) | Exemplar Case Study |")
        lines.append("| :--- | :--- | :---: | :---: | :--- |")

        for mode in self.FAILURE_MODES:
            cnt = counts.get(mode, 0)
            freq = freqs.get(mode, 0.0)
            desc = self.FAILURE_DESCRIPTIONS.get(mode, "")
            
            mode_studies = studies.get(mode, [])
            if mode_studies:
                first = mode_studies[0]
                exemplar = f"**{first['task_id']}**: {first['what_failed'][:65]}..."
            else:
                exemplar = "*None observed (0 failures)*"

            lines.append(f"| `{mode}` | {desc} | **{cnt}** | {freq:.1f}% | {exemplar} |")

        return "\n".join(lines)


def generate_comparative_markdown_table(analyzers: Dict[str, ErrorDiagnosticAnalyzer]) -> str:
    """
    Sinh bảng so sánh tổng hợp Error Taxonomy giữa các cấu hình (Ablation Comparison).
    """
    lines = []
    lines.append("### Comparative Error Taxonomy Across Ablation Configurations")
    lines.append("")
    
    header = "| Failure Mode | Description |"
    sep = "| :--- | :--- |"
    for name in analyzers.keys():
        header += f" {name} (Count / %) |"
        sep += " :---: |"
    lines.append(header)
    lines.append(sep)

    all_modes = ErrorDiagnosticAnalyzer.FAILURE_MODES
    for mode in all_modes:
        desc = ErrorDiagnosticAnalyzer.FAILURE_DESCRIPTIONS.get(mode, "")
        row = f"| `{mode}` | {desc} |"
        for name, an in analyzers.items():
            stats = an.get_statistics()
            cnt = stats["counts"].get(mode, 0)
            freq = stats["frequencies_percent"].get(mode, 0.0)
            row += f" {cnt} ({freq:.1f}%) |"
        lines.append(row)

    return "\n".join(lines)
