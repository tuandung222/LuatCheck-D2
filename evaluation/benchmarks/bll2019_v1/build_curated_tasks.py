import json,hashlib,tarfile
from pathlib import Path
corpus=json.loads(Path("data/corpus/labor_code_2019_official.json").read_text())
by_id={a["article_id"]:a for a in corpus}
prefix="Theo nguyên bản Bộ luật Lao động 45/2019/QH14 (không xét sửa đổi sau này), "
items=[
("PROBATION","single",prefix+"thời gian thử việc tối đa cho công việc cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên là bao nhiêu ngày?",["Dieu_25"],"Không quá 60 ngày.",[("Dieu_25","2. Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên;")]),
("PROBATION_WAGE","single",prefix+"tiền lương trong thời gian thử việc ít nhất bằng bao nhiêu phần trăm mức lương của công việc đó?",["Dieu_26"],"Ít nhất bằng 85% mức lương của công việc đó.",[("Dieu_26","Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức lương của công việc đó.")]),
("NOTICE","single",prefix+"người lao động có hợp đồng không xác định thời hạn muốn đơn phương chấm dứt trong trường hợp thông thường, không thuộc diện được miễn báo trước và không làm công việc đặc thù, phải báo trước ít nhất bao nhiêu ngày?",["Dieu_35"],"Ít nhất 45 ngày.",[("Dieu_35","a) Ít nhất 45 ngày nếu làm việc theo hợp đồng lao động không xác định thời hạn;")]),
("ABSENCE","single",prefix+"người lao động không thuộc diện được bảo vệ khỏi đơn phương chấm dứt, tự ý bỏ việc không có lý do chính đáng từ 05 ngày làm việc liên tục trở lên: người sử dụng lao động có quyền đơn phương chấm dứt không và có phải báo trước không?",["Dieu_36"],"Có quyền đơn phương chấm dứt; không phải báo trước.",[("Dieu_36","e) Người lao động tự ý bỏ việc mà không có lý do chính đáng từ 05 ngày làm việc liên tục trở lên;"),("Dieu_36","3. Khi đơn phương chấm dứt hợp đồng lao động quy định tại điểm d và điểm e khoản 1 Điều này thì người sử dụng lao động không phải báo trước cho người lao động.")]),
("PREGNANCY","single",prefix+"người sử dụng lao động có được thực hiện quyền đơn phương chấm dứt hợp đồng với lao động nữ đang mang thai hoặc người lao động đang nuôi con dưới 12 tháng tuổi không?",["Dieu_37"],"Không được thực hiện quyền đơn phương chấm dứt trong các trường hợp này.",[("Dieu_37","3. Người lao động nữ mang thai; người lao động đang nghỉ thai sản hoặc nuôi con dưới 12 tháng tuổi.")]),
("UNLAWFUL_RESIGNATION","single",prefix+"người lao động đơn phương chấm dứt trái pháp luật có được trợ cấp thôi việc không; khoản bồi thường cố định là bao nhiêu tháng tiền lương, chưa tính khoản ngày không báo trước và chi phí đào tạo?",["Dieu_40"],"Không được trợ cấp thôi việc; bồi thường nửa tháng tiền lương theo hợp đồng lao động.",[("Dieu_40","1. Không được trợ cấp thôi việc."),("Dieu_40","2. Phải bồi thường cho người sử dụng lao động nửa tháng tiền lương theo hợp đồng lao động và một khoản tiền tương ứng với tiền lương theo hợp đồng lao động trong những ngày không báo trước.")]),
("NOTICE_AND_SEVERANCE","synthesis",prefix+"một người lao động đang trong thời hạn hợp đồng 24 tháng muốn nghỉ đúng luật theo trường hợp thông thường, không được miễn báo trước và không làm công việc đặc thù. Người này đã làm việc thường xuyên đủ 12 tháng, chưa đủ điều kiện hưởng lương hưu. Cần báo trước bao lâu, mức trợ cấp thôi việc mỗi năm là bao nhiêu và thời gian đã tham gia bảo hiểm thất nghiệp có được tính vào trợ cấp không?",["Dieu_35","Dieu_46"],"Báo trước ít nhất 30 ngày. Mỗi năm làm việc được trợ cấp một nửa tháng tiền lương; trừ thời gian đã tham gia bảo hiểm thất nghiệp và thời gian đã được chi trả trợ cấp thôi việc, mất việc làm.",[("Dieu_35","b) Ít nhất 30 ngày nếu làm việc theo hợp đồng lao động xác định thời hạn có thời hạn từ 12 tháng đến 36 tháng;"),("Dieu_46","mỗi năm làm việc được trợ cấp một nửa tháng tiền lương"),("Dieu_46","trừ đi thời gian người lao động đã tham gia bảo hiểm thất nghiệp")]),
("UNLAWFUL_TERMINATION","synthesis",prefix+"đã xác định người sử dụng lao động đơn phương chấm dứt hợp đồng trái pháp luật, người lao động không muốn tiếp tục làm việc. Các nghĩa vụ chính về tiền lương, bảo hiểm, khoản tiền ít nhất bằng bao nhiêu tháng lương và trợ cấp thôi việc là gì?",["Dieu_41","Dieu_46"],"Phải trả tiền lương và đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp cho những ngày không được làm việc; trả thêm ít nhất 02 tháng tiền lương. Khi người lao động không muốn tiếp tục làm việc, trả thêm trợ cấp thôi việc theo Điều 46.",[("Dieu_41","phải trả tiền lương, đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp"),("Dieu_41","ít nhất bằng 02 tháng tiền lương theo hợp đồng lao động."),("Dieu_41","2. Trường hợp người lao động không muốn tiếp tục làm việc"),("Dieu_41","người sử dụng lao động phải trả trợ cấp thôi việc theo quy định tại Điều 46")]),
("DEPOSIT","single",prefix+"người sử dụng lao động yêu cầu người lao động nộp tiền đặt cọc chỉ để bảo đảm việc thực hiện hợp đồng lao động có được phép không?",["Dieu_17"],"Không được phép yêu cầu biện pháp bảo đảm bằng tiền hoặc tài sản khác cho việc thực hiện hợp đồng lao động.",[("Dieu_17","2. Yêu cầu người lao động phải thực hiện biện pháp bảo đảm bằng tiền hoặc tài sản khác cho việc thực hiện hợp đồng lao động.")]),
("FOREIGN_SCOPE","scope","Luật lao động của bang California quy định số giờ làm thêm tối đa là bao nhiêu giờ một tuần? Chỉ trả lời nếu cơ sở tri thức đã nạp có nguồn áp dụng cho bang này.",[],"Từ chối vì cơ sở tri thức chỉ có Bộ luật Lao động Việt Nam 2019, không có nguồn luật California.",[])
]
tasks=[]; review=[]
for n,(name,category,question,ids,answer,quotes) in enumerate(items,1):
    evidence=[]
    for aid,quote in quotes:
        assert quote in by_id[aid]["content"],(aid,quote)
        evidence.append({"article_id":aid,"exact_quote":quote,"pdf_pages":by_id[aid]["source_pages"]})
    tid=f"BLL19-{n:02d}-{name}"
    task={"task_id":tid,"category":category,"question":question,"ground_truth_article_ids":ids,
          "expected_behavior":"refuse" if not ids else "answer","expected_answer":answer,
          "reference_evidence":evidence,"provenance_status":"local_curated_statute_grounded",
          "gold_status":"source_checked_by_AI_not_expert_certified",
          "author":"OpenAI Codex: revision of local D2 draft, before any benchmark output",
          "scope":"Original 45/2019/QH14 Gazette snapshot; not current-law advice"}
    tasks.append(task)
    review.append({"task_id":tid,"status":"approved","reviewer":"OpenAI Codex (AI source review; not a human legal expert)",
                   "source_note":"Official Gazette PDF pages "+str(sorted({p for e in evidence for p in e['pdf_pages']})) if evidence else "Corpus scope: original Vietnamese Labour Code only, no California law.",
                   "gold_check":"All supporting excerpts checked as exact substrings of source-extracted articles; question conditions and terminology revised before inference.",
                   "expert_review":"pending"})
out=Path("evaluation/benchmarks/bll2019_v1");out.mkdir(parents=True,exist_ok=True)
def save(name,data): (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
save("tasks.json",tasks)
save("pilot4.json",[tasks[i] for i in [0,6,8,9]])
save("review.json",{"status":"approved","review_kind":"AI_source_review_not_human_expert",
                   "tasks_sha256":hashlib.sha256((out/"tasks.json").read_bytes()).hexdigest(),
                   "corpus_sha256":hashlib.sha256(Path("data/corpus/labor_code_2019_official.json").read_bytes()).hexdigest(),
                   "tasks":review,"public_benchmark_claim":False,"human_expert_review":"pending"})
manifest=json.loads(Path("docs/materials/benchmark-sources/corpus_manifest.json").read_text())
save("provenance.json",{"benchmark":"LuatCheck curated BLL2019-v1, 10 tasks","is_VLQA":False,
 "selection":"Six single-provision legal facts, two synthesis, one deposit prohibition, one foreign-scope refusal. Selected and fixed before observing native outputs.",
 "corpus":manifest,"corrections":["Removed internally inconsistent 3 years / 24-month contract scenario",
 "Replaced disciplinary dismissal with unlawful unilateral termination for Article 41",
 "Reclassified explicit contract-guarantee deposit as answerable under Article 17",
 "Added exceptions/conditions to notice-period questions; no assumption of full current-law coverage"],
 "limitations":["Small purposive local test set, not random or external held-out VLQA","Gold reviewed by AI against original source, not certified by legal expert",
 "Official public dataset release/provenance could not be confirmed for legacy VLQA IDs; ALQAC file access returned 401 and was not bypassed"]})
print("Frozen source-backed tasks:",len(tasks),"Corpus:",len(corpus))
