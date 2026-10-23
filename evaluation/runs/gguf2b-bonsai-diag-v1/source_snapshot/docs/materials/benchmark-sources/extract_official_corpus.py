"""Extract the complete 2019 Labour Code from the official Gazette PDF."""
import hashlib, json, re, unicodedata
from pathlib import Path
import pdfplumber
root = Path.cwd()
pdf_path = root/"docs/materials/benchmark-sources/bll2019-congbao.pdf"
with pdfplumber.open(pdf_path) as pdf:
    pages = []
    for page in pdf.pages:
        lines = [line for line in page.extract_text(x_tolerance=1.5).splitlines()
                 if "CÔNG BÁO/Số" not in line]
        pages.append(unicodedata.normalize("NFC", "\n".join(lines)))
text = "\n".join(pages)
matches = list(re.finditer(r"(?m)^Điều (\d+)\.\s*", text))
assert [int(m.group(1)) for m in matches] == list(range(1,221))
records = []
for i, match in enumerate(matches):
    end = matches[i+1].start() if i+1<len(matches) else len(text)
    article = text[match.start():end].strip()
    article = re.split(r"(?m)^(?:Chương [IVX]+|Mục \d+)\s*$", article)[0].strip()
    if i == len(matches)-1:
        article = article.split("CHỦ TỊCH QUỐC HỘI")[0].strip()
    title = article.splitlines()[0]
    # PDF line wrapping is normalized only by joining whitespace. No legal rewrite.
    content = re.sub(r"\s+", " ", article).strip()
    start_page = text[:match.start()].count("\n")  # replaced below with exact page offset map
    offset = 0
    containing = []
    for page_no, page_text in enumerate(pages, 1):
        next_offset = offset+len(page_text)+1
        if match.start() < next_offset and end > offset:
            containing.append(page_no)
        offset = next_offset
    records.append({"article_id": "Dieu_"+match.group(1), "law_id": "45/2019/QH14",
                    "law_name": "Bộ luật Lao động 2019 — nguyên bản Công báo 26-12-2019",
                    "title": title, "content": content,
                    "source_url": "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2019/11/30232/29070-1-2019993-99445-2019-qh14.pdf",
                    "source_pages": containing, "source_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
                    "extraction": "pdfplumber x_tolerance=1.5; remove running Gazette headers; NFC; join whitespace",
                    "scope": "Original 2019 enactment, not a consolidated statement of current 2026 law"})
out = root/"data/corpus/labor_code_2019_official.json"
out.write_text(json.dumps(records, ensure_ascii=False, indent=2)+"\n")
(root/"docs/materials/benchmark-sources/bll2019-clean-pages.json").write_text(json.dumps(pages,ensure_ascii=False))
manifest = {"source_url": records[0]["source_url"],"pdf_sha256":records[0]["source_sha256"],
            "records":len(records), "corpus_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
            "coverage":"Articles 1 through 220, no missing or duplicate article number",
            "snapshot_scope":records[0]["scope"], "not_a_public_QA_benchmark":True,
            "extractor": "docs/materials/benchmark-sources/extract_official_corpus.py"}
(root/"docs/materials/benchmark-sources/corpus_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
for number in [17,25,26,35,36,37,40,41,46,105,107]:
    record = records[number-1]
    print(record["article_id"], "PDF pages",record["source_pages"],record["content"])
