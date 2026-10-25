# Báo Cáo Thực Nghiệm & Phân Tích Chuyên Sâu: Đánh Giá Truy Hồi `google/embeddinggemma-2` (128-d vs 768-d) Trên Hệ Thống LuatCheck-D2

- **Ngày giờ lập báo cáo:** `2026-10-25 17:35:00+07:00` (Cập nhật bổ sung Weighted RRF lúc `2026-10-25 19:37:30+07:00` / `2026-10-25T12:37:30Z`)
- **Khung thời gian thực nghiệm:** `2026-10-25 05:11:47+07:00` $\rightarrow$ `2026-10-25 19:37:30+07:00`
- **Tác giả / Người thực hiện:** Võ Phạm Tuấn Dũng (`tuandung222` — `tuandung12092002@gmail.com`)
- **Repository:** [`tuandung222/LuatCheck-D2`](https://github.com/tuandung222/LuatCheck-D2) (nhánh `main`, commits `75703e9`, `5093613`, `c2cf676`)
- **Hugging Face Index Repositories (Public):**
  - Bản `128-d`: [`tuandunghcmut/luatcheck-embeddinggemma2-128d-indexes`](https://huggingface.co/datasets/tuandunghcmut/luatcheck-embeddinggemma2-128d-indexes)
  - Bản `768-d`: [`tuandunghcmut/luatcheck-embeddinggemma2-768d-indexes`](https://huggingface.co/datasets/tuandunghcmut/luatcheck-embeddinggemma2-768d-indexes)
- **Dữ liệu kết quả gốc (Raw JSON):** [`data/benchmarks/zalo_legal/retrieval_comparison_results.json`](../../data/benchmarks/zalo_legal/retrieval_comparison_results.json)

---

## 1. Nhật Ký Thời Gian Thực Nghiệm Chi Tiết (Execution Timeline)

Toàn bộ quá trình chuẩn bị dữ liệu, tích hợp kiến trúc, xây dựng chỉ mục (index building), chạy đánh giá truy hồi (retrieval benchmark) và xuất bản dữ liệu được ghi nhận theo múi giờ Việt Nam (`UTC+07:00`) và giờ chuẩn quốc tế (`UTC`):

| STT | Mốc thời gian (`UTC+07:00`) | Mốc thời gian (`UTC`) | Hạng mục công việc | Thời lượng / Kết quả |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `2026-10-25 05:11:47` | `2026-10-24T22:11:47Z` | Khởi tạo tích hợp `google/embeddinggemma-2` vào [`src/indexing/embeddings.py`](../../src/indexing/embeddings.py), bổ sung `truncate_dim`, `config_kwargs`, `bfloat16` guard và `AutoTokenizer` fallback. | Hoàn tất tích hợp core embedding |
| 2 | `2026-10-25 05:15:10` | `2026-10-24T22:15:10Z` | Tích hợp `IndexedRetriever` vào [`src/retrieval/hybrid_domain.py`](../../src/retrieval/hybrid_domain.py), [`src/pipeline/builder.py`](../../src/pipeline/builder.py), [`src/api/runtime.py`](../../src/api/runtime.py) và Web Demo UI ([`SystemBar.tsx`](../../frontend/src/SystemBar.tsx)). | Tương thích 100% với Harness & Web UI |
| 3 | `2026-10-25 05:18:51` | `2026-10-24T22:18:51Z` | Build index `labor_code_2019_gemma2_128d` (220 điều, 231 chunks, 4 vector stores + FTS5). | `35.05s` (`10.03 chunks/s`) |
| 4 | `2026-10-25 05:20:10` | `2026-10-24T22:20:10Z` | Build index `labour_vi_v1_gemma2_128d` (458 điều, 531 chunks, 4 vector stores + FTS5). | `78.21s` (`8.20 chunks/s`) |
| 5 | `2026-10-25 05:20:53` | `2026-10-24T22:20:53Z` | Build index `hcmut_academic_v1_gemma2_128d` (143 mục, 206 chunks, 4 vector stores + FTS5). | `37.84s` (`8.31 chunks/s`) |
| 6 | `2026-10-25 05:39:32` | `2026-10-24T22:39:32Z` | Build index `zalo_legal_gemma2_128d` (1,000 văn bản Hard-Negative Pool từ 61,425 điều luật Zalo AI, 1,644 chunks). | `179.07s` (`9.95 chunks/s`) |
| 7 | `2026-10-25 05:45:00` | `2026-10-24T22:45:00Z` | Đánh giá lượt 1 (`128-d` vs `BM25+TF-IDF RRF` vs `FTS5`), push code lên `origin/main` (`75703e9`) và xuất bản bộ index `128-d` lên Hugging Face Hub. | Hoàn tất đánh giá `128-d` |
| 8 | `2026-10-25 06:00:35` | `2026-10-24T23:00:35Z` | Build index `labor_code_2019_gemma2_768d` (220 điều, 231 chunks, full `768-d`). | `17.92s` (`14.48 chunks/s`) |
| 9 | `2026-10-25 06:00:55` | `2026-10-24T23:00:55Z` | Build index `hcmut_academic_v1_gemma2_768d` (143 mục, 206 chunks, full `768-d`). | `19.95s` (`10.66 chunks/s`) |
| 10 | `2026-10-25 06:01:39` | `2026-10-24T23:01:39Z` | Build index `labour_vi_v1_gemma2_768d` (458 điều, 531 chunks, full `768-d`). | `44.11s` (`12.35 chunks/s`) |
| 11 | `2026-10-25 06:04:39` | `2026-10-24T23:04:39Z` | Build index `zalo_legal_gemma2_768d` (1,000 văn bản Hard-Negative Pool, 1,644 chunks, full `768-d`). | `180.47s` (`9.27 chunks/s`) |
| 12 | `2026-10-25 06:08:15` | `2026-10-24T23:08:15Z` | Chạy benchmark tổng thể so sánh 12 cấu hình (`Lexical`, `128-d`, `768-d`, `Hybrid RRF`) trên cả 4 tập dữ liệu; xuất bản bộ index `768-d` lên Hugging Face Hub và push commit `5093613` lên `origin/main`. | Hoàn tất đánh giá `768-d` RRF 1:1 |
| 13 | `2026-10-25 19:37:30` | `2026-10-25T12:37:30Z` | Cập nhật `HybridSearcher` & `IndexedRetriever` sang **Weighted RRF (`0.75 * FTS5 + 0.25 * Vector 768-d`)**, trỏ mặc định các profile demo/harness sang bộ index `768-d` (`store: numpy`), và chạy đánh giá xác nhận trên cả 4 tập benchmark. | Đạt hạng #1 toàn diện trên `zalo_legal` |

---

## 2. Cấu Hình Phần Cứng, Phần Mềm & Mô Hình (Experimental Setup)

### 2.1. Môi trường thực thi
- **Hệ điều hành & Kiến trúc:** `macOS-27.0.1-arm64-arm-64bit-Mach-O` (Apple Silicon `arm64`, tăng tốc phần cứng qua `MPS` — Metal Performance Shaders).
- **Ngôn ngữ & Thư viện:**
  - `Python`: `3.14.4`
  - `PyTorch`: `2.14.1` (`device="mps"`, `dtype="bfloat16"`)
  - `transformers`: `5.20.2`
  - `sentence-transformers`: `6.2.0`
  - `faiss-cpu`: `1.15.1`
  - `qdrant-client`: `1.20.0`
  - `sqlite3`: `3.53.0` (tích hợp `FTS5` BM25)

### 2.2. Cấu hình mô hình `google/embeddinggemma-2`
- **Model ID & Revision:** [`google/embeddinggemma-2`](https://huggingface.co/google/embeddinggemma-2) — commit `914f7f89142e33e77833254d9c9b90c3cef7303b`.
- **Cơ chế nạp Text-Only 270M Backbone:**
  - Mặc định checkpoint `google/embeddinggemma-2` trên Hugging Face đóng gói kèm tower thị giác và âm thanh (`EmbeddingGemma2Model` tổng ~0.9B tham số).
  - Hệ thống đã cấu hình `config_kwargs={"vision_config": None, "audio_config": None}` để chỉ nạp **Text Backbone 270M tham số**, giúp bộ nhớ GPU trên Mac (`mps_allocated_mb`) chỉ chiếm đúng **`516.9 MB`** ở chế độ `bfloat16`.
- **Prompt Prefix chuẩn theo thiết kế của Google:**
  - Truy vấn (`query_prefix`): `"task: search result | query: "`
  - Văn bản (`document_prefix`): `"title: none | text: "`
- **Chuẩn hóa & Cắt chiều Matryoshka (MRL):**
  - `normalize_embeddings = True` (chuẩn hóa L2 sau khi cắt chiều).
  - Thử nghiệm ở 2 mức chiều: **`truncate_dim = 128`** (nhỏ gọn) và **`truncate_dim = 768`** (chiều tối đa của mô hình).
- **Cấu hình phân đoạn văn bản (Chunking):**
  - Chiến lược: `article_sections` (ưu tiên giữ nguyên vẹn từng Điều/Mục; nếu điều luật dài quá ngưỡng mới tách theo Khoản kèm câu mở đầu của Điều).
  - `max_tokens = 512`, `overlap_tokens = 64`.

---

## 3. Chi Phí Thời Gian Build Index & Dung Lượng Lưu Trữ (`128-d` vs `768-d`)

### 3.1. Bảng so sánh thời gian build và tốc độ xử lý

> [!NOTE]
> Ở lượt build `768-d`, cả 4 bộ dữ liệu được chạy chung trong một tiến trình với `shared_provider` (chỉ nạp trọng số mô hình `google/embeddinggemma-2` lên `MPS` đúng 1 lần duy nhất), giúp loại bỏ ~15–20 giây overhead khởi tạo model ở các tập nhỏ.

| Bộ dữ liệu (Corpus) | Số văn bản (Records) | Số đoạn (Chunks) | Thời gian build `128-d` | Tốc độ `128-d` | Thời gian build `768-d` | Tốc độ `768-d` |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **`labor_code_2019`** (BLLĐ 2019) | 220 | 231 | `35.05 s` | `10.03 chunks/s` | `17.92 s` | `14.48 chunks/s` |
| **`hcmut_academic_v1`** (Quy chế ĐHBK) | 143 | 206 | `37.84 s` | `8.31 chunks/s` | `19.95 s` | `10.66 chunks/s` |
| **`labour_vi_v1`** (Đa văn bản Lao động) | 458 | 531 | `78.21 s` | `8.20 chunks/s` | `44.11 s` | `12.35 chunks/s` |
| **`zalo_legal_hard1k`** (Zalo Legal 1K Pool) | 1,000 | 1,644 | `179.07 s` | `9.95 chunks/s` | `180.47 s` | `9.27 chunks/s` |
| **TỔNG CỘNG (4 bộ)** | **1,821** | **2,612** | **`330.17 s` (`5p 30s`)** | **`9.12 chunks/s`** | **`262.45 s` (`4p 22s`)** | **`9.95 chunks/s`** |

### 3.2. Bảng so sánh dung lượng đĩa (Disk Size) theo từng Backend

| Bộ dữ liệu | Chiều Vector | `NumPy` (`.npy` + `.jsonl`) | `FAISS Flat` (`IndexFlatIP`) | `FAISS HNSW` (`IndexHNSWFlat`) | `Qdrant Local` (SQLite) | `SQLite FTS5` (`fts5.sqlite`) |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: |
| **`labor_code_2019`** (231 chunks) | `128-d` | `283.4 KB` | `288.9 KB` | `350.0 KB` | `960.6 KB` | `656.0 KB` |
| **`labor_code_2019`** (231 chunks) | `768-d` | `860.9 KB` | `866.4 KB` | `927.5 KB` | `1,884.6 KB` | `656.0 KB` |
| **`hcmut_academic_v1`** (206 chunks) | `128-d` | `318.0 KB` | `326.5 KB` | `381.0 KB` | `856.6 KB` | `608.0 KB` |
| **`hcmut_academic_v1`** (206 chunks) | `768-d` | `833.0 KB` | `841.5 KB` | `896.0 KB` | `1,776.6 KB` | `608.0 KB` |
| **`labour_vi_v1`** (531 chunks) | `128-d` | `866.5 KB` | `884.2 KB` | `1,024.7 KB` | `2,188.6 KB` | `1,812.0 KB` |
| **`labour_vi_v1`** (531 chunks) | `768-d` | `2,194.0 KB` | `2,211.7 KB` | `2,352.2 KB` | `4,568.6 KB` | `1,812.0 KB` |
| **`zalo_legal_hard1k`** (1,644 chunks) | `128-d` | `1,415.7 KB` | `1,474.6 KB` | `1,910.8 KB` | `3,448.6 KB` | `5,488.0 KB` |
| **`zalo_legal_hard1k`** (1,644 chunks) | `768-d` | `5,525.7 KB` | `5,584.6 KB` | `6,020.8 KB` | `13,316.6 KB` | `5,488.0 KB` |

---

## 4. Kết Quả Đánh Giá Truy Hồi Chi Tiết Trên 4 Tập Benchmark

Các chỉ số đánh giá tiêu chuẩn Information Retrieval (IR) gồm:
- **`Recall@k` (`k = 1, 5, 10, 20`)**: Tỉ lệ phần trăm các điều luật đích (gold articles) xuất hiện trong `Top-k` kết quả trả về.
- **`MRR@10` (Mean Reciprocal Rank @ 10)**: Trung bình nghịch đảo thứ hạng của điều luật đúng đầu tiên trong `Top-10`.
- **`NDCG@10` (Normalized Discounted Cumulative Gain @ 10)**: Đánh giá chất lượng sắp xếp có tính đến thứ hạng và số lượng văn bản đích tìm được.
- **`MAP@10` (Mean Average Precision @ 10)**: Độ chính xác trung bình tại `Top-10`.

---

### 4.1. Tập 1: `zalo_legal_hard1k` — GreenNode / Zalo AI Legal Retrieval (818 truy vấn test)

- **Thiết kế tập đánh giá:** Bao gồm toàn bộ **818 câu hỏi test** (tương ứng **447 điều luật đích** độc nhất) và **553 điều luật gây nhiễu khó nhất (top hard negatives)** được lọc bằng `FTS5 BM25` từ tổng kho **61,425 điều luật** của Việt Nam, tạo thành tập **1,000 điều luật (1,644 chunks)**. Ngoài ra, báo cáo cũng ghi nhận kết quả chạy `SQLite FTS5` trực tiếp trên toàn bộ **61,425 điều luật** để làm mốc tham chiếu.

| Hạng (theo MRR@10) | Phương pháp Truy hồi | `Recall@1` | `Recall@5` | `Recall@10` | `Recall@20` | `MRR@10` | `NDCG@10` | `MAP@10` | Độ trễ tổng (`ms/q`) | Độ trễ tìm kiếm thuần (`ms/q`) |
| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | **`EmbeddingGemma-2 768-d Weighted RRF` (`0.75*FTS5 + 0.25*Vec768d`)** | **`69.07%`** | **`97.00%`** | **`98.90%`** | **`99.51%`** | **`80.94%`** | **`85.32%`** | **`80.74%`** | `21.75 ms` | `~3.65 ms` |
| **2** | **`SQLite FTS5 Keyword` (1K Hard Pool)** | `68.83%` | `95.78%` | `98.78%` | `99.14%` | `80.20%` | `84.73%` | `80.05%` | `3.58 ms` | `3.58 ms` |
| **3** | **`EmbeddingGemma-2 768-d Hybrid RRF 1:1` (`FTS5 + Vector 768d`)** | `66.99%` | `94.56%` | `98.53%` | `99.39%` | `78.92%` | `83.68%` | `78.72%` | `21.77 ms` | `~3.65 ms` |
| **4** | **`LuatCheck BM25 + TF-IDF 1–3-gram RRF` (Hiện tại)** | `62.47%` | `93.22%` | `98.17%` | `99.27%` | `75.43%` | `80.99%` | `75.34%` | `5.24 ms` | `5.24 ms` |
| **5** | **`EmbeddingGemma-2 128-d Hybrid RRF 1:1` (`FTS5 + Vector 128d`)** | `59.90%` | `91.26%` | `96.27%` | `99.27%` | `73.34%` | `78.83%` | `73.05%` | `12.12 ms` *(batch)* / `52.44 ms` *(lẻ)* | `~3.65 ms` |
| **6** | **`LuatCheck BM25-only`** | `58.68%` | `91.63%` | `96.64%` | `98.41%` | `72.62%` | `78.50%` | `72.53%` | **`1.85 ms`** | **`1.85 ms`** |
| **7** | **`EmbeddingGemma-2 768-d Vector-only` (`FAISS HNSW`)** | `52.93%` | `83.68%` | `90.28%` | `94.19%` | `66.13%` | `71.88%` | `65.86%` | `18.28 ms` | `0.172 ms` |
| **8** | **`EmbeddingGemma-2 768-d Vector-only` (`NumPy` / `FAISS Flat`)** | `52.93%` | `83.68%` | `90.28%` | `94.07%` | `66.13%` | `71.88%` | `65.86%` | `18.18 ms` | `0.069 ms` (`NumPy`) / `0.155 ms` (`FAISS`) |
| **9** | **`EmbeddingGemma-2 128-d Vector-only` (`FAISS HNSW`)** | `39.98%` | `69.01%` | `80.87%` | `88.33%` | `53.62%` | `60.04%` | `53.37%` | `8.60 ms` | `0.138 ms` |
| **10** | **`EmbeddingGemma-2 128-d Vector-only` (`NumPy` / `FAISS Flat` / `Qdrant`)** | `39.98%` | `69.01%` | `80.75%` | `88.33%` | `53.61%` | `60.01%` | `53.35%` | `8.52–8.99 ms` | `0.065 ms` (`NumPy`) / `0.529 ms` (`Qdrant`) |
| *Tham chiếu* | *`SQLite FTS5` trên toàn bộ **61,425 điều luật** (Full Corpus)* | *`56.11%`* | *`83.44%`* | *`88.45%`* | *`92.11%`* | *`68.07%`* | *`72.98%`* | *`67.88%`* | *`152.24 ms`* | *`152.24 ms`* |

---

### 4.2. Tập 2: `bll2019_v1` — Bộ luật Lao động 2019 (220 điều luật, 9 truy vấn answerable)

| Hạng | Phương pháp Truy hồi | `Recall@1` | `Recall@5` | `Recall@10` | `Recall@20` | `MRR@10` | `NDCG@10` | `MAP@10` | Tìm kiếm thuần (`ms/q`) |
| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | **`LuatCheck BM25 + TF-IDF 1–3-gram RRF`** | **`77.78%`** | **`100.00%`** | **`100.00%`** | **`100.00%`** | **`94.44%`** | **`93.34%`** | **`89.26%`** | `1.86 ms` |
| **1** | **`LuatCheck BM25-only`** | **`77.78%`** | **`100.00%`** | **`100.00%`** | **`100.00%`** | **`94.44%`** | **`93.34%`** | **`89.26%`** | **`1.06 ms`** |
| **3** | **`SQLite FTS5 Keyword`** | **`77.78%`** | `94.44%` | **`100.00%`** | **`100.00%`** | **`94.44%`** | `93.14%` | `88.89%` | `3.66 ms` |
| **4** | **`EmbeddingGemma-2 768-d Weighted RRF` (`0.75*FTS5 + 0.25*Vec768d`)** | **`77.78%`** | `94.44%` | **`100.00%`** | **`100.00%`** | **`94.44%`** | `92.66%` | `87.96%` | `~3.76 ms` |
| **5** | **`EmbeddingGemma-2 768-d Hybrid RRF 1:1` (`FTS5 + Vector 768d`)** | **`77.78%`** | `88.89%` | **`100.00%`** | **`100.00%`** | `92.59%` | `90.55%` | `84.92%` | `~3.76 ms` |
| **6** | **`EmbeddingGemma-2 768-d Vector-only` (`NumPy` / `FAISS Flat` / `HNSW`)** | `44.44%` | `77.78%` | **`100.00%`** | **`100.00%`** | `67.96%` | `71.25%` | `59.55%` | `0.098–0.324 ms` |
| **7** | **`EmbeddingGemma-2 128-d Hybrid RRF 1:1` (`FTS5 + Vector 128d`)** | `33.33%` | `83.33%` | `88.89%` | **`100.00%`** | `61.48%` | `65.28%` | `55.46%` | `~3.72 ms` |
| **8** | **`EmbeddingGemma-2 128-d Vector-only` (`NumPy` / `FAISS` / `Qdrant`)** | `11.11%` | `61.11%` | `72.22%` | `83.33%` | `40.37%` | `43.65%` | `32.04%` | `0.061–0.535 ms` |

---

### 4.3. Tập 3: `labour_vi_v1` — Đa văn bản Pháp luật Lao động (458 điều luật, 45 truy vấn answerable)

| Hạng | Phương pháp Truy hồi | `Recall@1` | `Recall@5` | `Recall@10` | `Recall@20` | `MRR@10` | `NDCG@10` | `MAP@10` | Tìm kiếm thuần (`ms/q`) |
| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | **`SQLite FTS5 Keyword`** | **`84.44%`** | **`100.00%`** | **`100.00%`** | **`100.00%`** | `94.81%` | **`96.43%`** | **`95.19%`** | `4.83 ms` |
| **2** | **`LuatCheck BM25 + TF-IDF 1–3-gram RRF`** | **`84.44%`** | `98.89%` | `98.89%` | **`100.00%`** | **`95.19%`** | `95.69%` | `94.07%` | `2.72 ms` |
| **3** | **`EmbeddingGemma-2 768-d Weighted RRF` (`0.75*FTS5 + 0.25*Vec768d`)** | `82.22%` | **`100.00%`** | **`100.00%`** | **`100.00%`** | `94.07%` | `95.54%` | `93.70%` | `~4.91 ms` |
| **4** | **`LuatCheck BM25-only`** | `80.00%` | `98.89%` | `98.89%` | `98.89%` | `92.41%` | `93.33%` | `90.72%` | **`1.59 ms`** |
| **5** | **`EmbeddingGemma-2 768-d Hybrid RRF 1:1` (`FTS5 + Vector 768d`)** | `75.56%` | `97.78%` | **`100.00%`** | **`100.00%`** | `87.91%` | `90.12%` | `86.14%` | `~4.91 ms` |
| **6** | **`EmbeddingGemma-2 128-d Hybrid RRF 1:1` (`FTS5 + Vector 128d`)** | `66.67%` | `91.11%` | `95.56%` | `98.89%` | `80.44%` | `84.05%` | `79.86%` | `~4.90 ms` |
| **7** | **`EmbeddingGemma-2 768-d Vector-only` (`NumPy` / `FAISS Flat` / `HNSW`)** | `54.44%` | `84.44%` | `90.00%` | `98.89%` | `71.21%` | `74.51%` | `68.48%` | `0.079–0.187 ms` |
| **8** | **`EmbeddingGemma-2 128-d Vector-only` (`NumPy` / `FAISS` / `Qdrant`)** | `41.11%` | `67.78%` | `86.67%` | `92.22%` | `55.87%` | `62.66%` | `54.63%` | `0.065–0.463 ms` |

---

### 4.4. Tập 4: `hcmut_v1` — Quy chế Học vụ ĐH Bách Khoa ĐHQG-HCM (143 mục, 45 truy vấn answerable)

| Hạng | Phương pháp Truy hồi | `Recall@1` | `Recall@5` | `Recall@10` | `Recall@20` | `MRR@10` | `NDCG@10` | `MAP@10` | Tìm kiếm thuần (`ms/q`) |
| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | **`SQLite FTS5 Keyword`** | **`90.00%`** | **`100.00%`** | **`100.00%`** | **`100.00%`** | **`97.78%`** | **`97.64%`** | **`96.30%`** | `1.57 ms` |
| **2** | **`EmbeddingGemma-2 768-d Weighted RRF` (`0.75*FTS5 + 0.25*Vec768d`)** | `88.89%` | `96.67%` | `98.89%` | **`100.00%`** | `95.78%` | `95.36%` | `93.44%` | `~1.64 ms` |
| **3** | **`LuatCheck BM25 + TF-IDF 1–3-gram RRF`** | `85.56%` | `98.89%` | **`100.00%`** | **`100.00%`** | `95.19%` | `95.51%` | `93.33%` | `1.17 ms` |
| **4** | **`LuatCheck BM25-only`** | `86.67%` | `98.89%` | `98.89%` | **`100.00%`** | `95.19%` | `95.16%` | `93.15%` | **`1.07 ms`** |
| **5** | **`EmbeddingGemma-2 768-d Hybrid RRF 1:1` (`FTS5 + Vector 768d`)** | `77.78%` | `95.56%` | `96.67%` | `98.89%` | `89.63%` | `90.29%` | `87.24%` | `~1.64 ms` |
| **6** | **`EmbeddingGemma-2 128-d Hybrid RRF 1:1` (`FTS5 + Vector 128d`)** | `65.56%` | `91.11%` | `92.22%` | `95.56%` | `80.44%` | `81.59%` | `76.72%` | `~1.62 ms` |
| **7** | **`EmbeddingGemma-2 768-d Vector-only` (`NumPy` / `FAISS Flat` / `HNSW`)** | `61.11%` | `88.89%` | `94.44%` | `95.56%` | `77.08%` | `79.74%` | `73.74%` | `0.071–0.151 ms` |
| **8** | **`EmbeddingGemma-2 128-d Vector-only` (`NumPy` / `FAISS` / `Qdrant`)** | `40.00%` | `74.44%` | `88.89%` | `88.89%` | `57.71%` | `64.63%` | `56.15%` | `0.052–0.390 ms` |

---

## 5. Phân Tích Chuyên Sâu & Technical Insights

### Insight 1: Tại sao Lexical Search (`SQLite FTS5` / `BM25 + TF-IDF RRF`) vượt xa Dense Vector thuần túy trên văn bản pháp luật Việt Nam?

Nhìn vào bảng số liệu trên cả 4 tập dữ liệu, phương pháp tìm kiếm từ khóa (`SQLite FTS5` và `BM25 + TF-IDF 1–3-gram RRF`) luôn thắng áp đảo `Vector-only` (kể cả ở `768-d`). Nguyên nhân không phải do lỗi kỹ thuật mà nằm ở **đặc trưng cấu trúc của văn bản quy phạm pháp luật và cách đặt câu hỏi**:

1. **Mật độ cao của các từ khóa định danh chính xác (Exact Lexical Anchors):**
   - Văn bản luật Việt Nam và quy chế học vụ chứa rất nhiều con số, ký hiệu định khoản và cụm từ chuyên ngành cố định: số hiệu nghị định (`145/2020/NĐ-CP`), thời hạn (`06 ngày làm việc`, `45 ngày`, `30 ngày`), tỉ lệ phần trăm (`150%`, `200%`, `300%`), tên thủ tục (`đơn phương chấm dứt hợp đồng lao động`, `trợ cấp thôi việc`, `cảnh cáo học vụ`).
   - `BM25` / `FTS5` đánh trọng số IDF rất cao cho các token hiếm này. Chỉ cần câu hỏi chứa cụm `"thử việc không quá 60 ngày"` hoặc `"báo trước ít nhất 45 ngày"`, thuật toán từ khóa tìm trúng ngay điều luật đích ở vị trí `Top-1` (`Recall@1` đạt `68.83%` trên Zalo Legal và `84.44%–90.00%` trên Labour/HCMUT).
2. **Hiện tượng "gom cụm theo chủ đề" (Topic Crowding) của Dense Embedding chưa fine-tune chuyên ngành:**
   - `google/embeddinggemma-2` (270M text backbone) là mô hình đa ngôn ngữ tổng quát. Trong không gian cosine của mô hình, hàng chục điều luật cùng quy định về *"hợp đồng lao động"* (từ Điều 13 đến Điều 48 Bộ luật Lao động) có vector biểu diễn rất gần nhau.
   - Khi người dùng hỏi một chi tiết cụ thể bên trong một điều luật dài, phép nhân vô hướng vector thường bị nhiễu bởi các điều luật lân cận có cùng chủ đề chung, khiến điều luật đúng bị đẩy từ hạng 1 xuống hạng 3–10 (`Recall@1` của `768-d Vector-only` chỉ đạt `52.93%`, nhưng `Recall@10` đạt tới `90.28%` và `Recall@20` đạt `94.07%`).

---

### Insight 2: Đánh giá thực chất Matryoshka Representation Learning (MRL) — Cắt chiều `128-d` mất gì và được gì so với `768-d`?

| Chỉ số trên `zalo_legal` (818 truy vấn) | Bản `128-d` | Bản `768-d` | Chênh lệch (`768-d` so với `128-d`) |
| :--- | ---: | ---: | ---: |
| **`Vector-only Recall@1`** | `39.98%` | `52.93%` | **`+12.95%`** (tăng tương đối `+32.4%`) |
| **`Vector-only Recall@5`** | `69.01%` | `83.68%` | **`+14.67%`** |
| **`Vector-only Recall@10`** | `80.75%` | `90.28%` | **`+9.53%`** |
| **`Vector-only MRR@10`** | `53.61%` | `66.13%` | **`+12.52%`** |
| **`Hybrid RRF Recall@1`** | `59.90%` | `66.99%` | **`+7.09%`** |
| **`Hybrid RRF MRR@10`** | `73.34%` | `78.92%` | **`+5.58%`** |
| **Thời gian build index (1,644 chunks)** | `179.07 s` | `180.47 s` | Chênh lệch không đáng kể (`+1.40 s`) |
| **Dung lượng đĩa (`NumPy` / `FAISS Flat`)** | `1.42 MB` | `5.53 MB` | Tăng `3.9x` (nhưng vẫn cực nhỏ, `< 6 MB`) |

**Kết luận kỹ thuật về MRL (`128-d` vs `768-d`):**
1. **Không tiết kiệm thời gian tính toán khi tạo embedding:** Thời gian build index và encode câu hỏi phụ thuộc vào forward pass qua 270 triệu tham số của mạng Transformer trên GPU (`MPS`), vốn y hệt nhau giữa `128-d` và `768-d`. Việc cắt lấy 128 phần tử đầu tiên của vector 768 chiều (`vec[:128]`) chỉ diễn ra ở tầng cuối cùng.
2. **Suy giảm độ phân giải ngữ nghĩa pháp lý nghiêm trọng ở `128-d`:** Trong cơ chế huấn luyện Matryoshka, 128 chiều đầu tiên nén thông tin chủ đề thô (coarse topic: *lao động, hình sự, đất đai, học vụ*). Các chiều từ `129` đến `768` mới lưu giữ các đặc trưng phân biệt chi tiết (fine-grained legal qualifiers: *đối tượng áp dụng, điều kiện ngoại lệ, mức phạt, thời hạn*). Do đó, trên bài toán luật học đòi hỏi độ chính xác điều khoản cao, **tuyệt đối không nên cắt xuống `128-d` khi dung lượng bộ nhớ cho `768-d` chỉ tốn vài MB**.

---

### Insight 3: Nghịch lý "Unweighted 50/50 RRF" — Tại sao ghép `FTS5 + Vector` theo tỉ lệ 1:1 lại làm giảm nhẹ `Recall@1` của `FTS5`, nhưng lại lập đỉnh ở `Recall@20`?

Trong [`src/retrieval/hybrid_domain.py`](../../src/retrieval/hybrid_domain.py), hàm `IndexedRetriever.search` đang kết hợp thứ hạng của nhánh `Vector` ($r_{\text{vec}}$) và nhánh `FTS5` ($r_{\text{fts}}$) theo công thức Reciprocal Rank Fusion (RRF) không trọng số (1:1) với $k = 60$:

$$\text{score}_{\text{RRF}}(d) = \frac{1}{60 + r_{\text{vec}}(d)} + \frac{1}{60 + r_{\text{fts}}(d)}$$

Phân tích toán học trực tiếp trên công thức này giải thích rõ hai hiện tượng trái ngược trong bảng kết quả:

1. **Tại sao `Recall@1` của `Hybrid RRF` (`66.99%` ở `768-d`, `59.90%` ở `128-d`) thấp hơn `FTS5` độc lập (`68.83%`)?**
   - Giả sử với một câu hỏi có từ khóa rõ ràng, `FTS5` tìm đúng điều luật đích $d^*$ ở hạng 1 ($r_{\text{fts}}(d^*) = 1$), nhưng nhánh `Vector` (do nhiễu chủ đề) đẩy $d^*$ xuống hạng 25 ($r_{\text{vec}}(d^*) = 25$). Khi đó:
     $$\text{score}_{\text{RRF}}(d^*) = \frac{1}{60 + 25} + \frac{1}{60 + 1} = \frac{1}{85} + \frac{1}{61} \approx 0.02816$$
   - Trong khi đó, một điều luật gây nhiễu $d_{\text{noise}}$ cùng chủ đề được cả hai nhánh xếp ở hạng 2 ($r_{\text{vec}}(d_{\text{noise}}) = 2, r_{\text{fts}}(d_{\text{noise}}) = 2$) sẽ có điểm:
     $$\text{score}_{\text{RRF}}(d_{\text{noise}}) = \frac{1}{62} + \frac{1}{62} \approx 0.03226 > 0.02816$$
   - Kết quả là $d_{\text{noise}}$ vượt lên hạng 1, đẩy $d^*$ xuống hạng 2. Việc trao quyền biểu quyết ngang bằng (`50/50`) giữa một mô hình giỏi bắt chính xác điều khoản (`FTS5`, `R@1 = 68.83%`) và một mô hình yếu hơn ở vị trí đầu (`Vector`, `R@1 = 52.93%` ở `768-d` hoặc `39.98%` ở `128-d`) làm giảm độ chính xác tại `Top-1`.
2. **Tại sao `Recall@20` của `768-d Hybrid RRF` đạt `99.39%` — vượt cả `FTS5` (`99.14%`) và `BM25+TF-IDF` (`99.27%`), và khi nâng lên `Weighted RRF (0.75 * FTS5 + 0.25 * Vector 768-d)` thì đứng #1 ở MỌI chỉ số?**
   - Với ~`0.86%` số câu hỏi mà người dùng diễn đạt hoàn toàn bằng ngôn ngữ đời thường (không khớp từ khóa với văn bản luật), `FTS5` không trả về điều luật đúng trong `Top-20`, nhưng `768-d Vector` vẫn xếp điều luật đúng trong nhóm dẫn đầu, giúp `Hybrid RRF` kéo điều luật đó vào `Top-20`.
   - Khi áp dụng **Weighted RRF** ($w_{\text{fts}} = 0.75, w_{\text{vec}} = 0.25$):
     $$\text{score}_{\text{WRRF}}(d) = 0.75 \cdot \frac{1}{60 + r_{\text{fts}}(d)} + 0.25 \cdot \frac{1}{60 + r_{\text{vec}}(d)}$$
     Phương pháp **`EmbeddingGemma-2 768-d Weighted RRF`** lập tức **vượt qua cả `SQLite FTS5` lẫn `LuatCheck BM25 + TF-IDF RRF` trên tất cả các thước đo của tập `zalo_legal` (818 truy vấn)**:
     - `Recall@1`: tăng từ `66.99%` lên **`69.07%`** (vượt `FTS5` `68.83%` và `BM25+TF-IDF` `62.47%`).
     - `Recall@5`: tăng từ `94.56%` lên **`97.00%`** (vượt `FTS5` `95.78%` và `BM25+TF-IDF` `93.22%`).
     - `Recall@10`: tăng từ `98.53%` lên **`98.90%`** (vượt `FTS5` `98.78%` và `BM25+TF-IDF` `98.17%`).
     - `Recall@20`: tăng từ `99.39%` lên **`99.51%`** (cao nhất toàn bộ thực nghiệm).
     - `MRR@10`: tăng từ `78.92%` lên **`80.94%`** (vượt `FTS5` `80.20%` và `BM25+TF-IDF` `75.43%`).
     - Trên `labour_vi_v1`, `Recall@1` tăng từ `75.56%` lên **`82.22%`** (`Recall@5 = 100.0%`); trên `hcmut_v1`, `Recall@1` tăng từ `77.78%` lên **`88.89%`** (`MRR@10 = 95.78%`, vượt `BM25+TF-IDF` `95.19%`).

---

### Insight 4: So sánh 4 Vector Store Backends (`NumPy` vs `FAISS Flat` vs `FAISS HNSW` vs `Qdrant Local`)

Trên quy mô corpus từ `200` đến `2,000` chunks (và thậm chí lên đến `10,000` chunks):

| Tiêu chí | `NumPy` (`vectors.npy`) | `FAISS Flat` (`IndexFlatIP`) | `FAISS HNSW` (`IndexHNSWFlat`) | `Qdrant Local` (`qdrant-client`) |
| :--- | :--- | :--- | :--- | :--- |
| **Độ chính xác (`Recall@k`, `MRR`)** | Chính xác tuyệt đối (100% exact) | Chính xác tuyệt đối (100% exact) | Xấp xỉ (lệch $\pm 0.1\%$ ở `R@10/20`) | Chính xác tuyệt đối (100% exact) |
| **Tốc độ tìm kiếm thuần (`768-d`, 1,644 chunks)** | **`0.069 ms / query`** (Nhanh nhất) | `0.155 ms / query` | `0.172 ms / query` | `0.529 ms / query` |
| **Dung lượng lưu trữ (`768-d`, 1,644 chunks)** | **`5.53 MB`** (Nhỏ nhất) | `5.58 MB` | `6.02 MB` (+8% lưu đồ thị cạnh) | `13.32 MB` (+140% overhead SQLite) |
| **Độ phức tạp triển khai** | Không cần thư viện C++ ngoài | Cần `faiss-cpu` | Cần `faiss-cpu` | Cần `qdrant-client` |
| **Khi nào nên dùng?** | **Khuyên dùng mặc định** cho `< 20,000` chunks (như BLLĐ, Quy chế HCMUT) | Khi tích hợp pipeline chuẩn FAISS từ `10,000–100,000` chunks | Chỉ có lợi thế tốc độ khi corpus `> 50,000` chunks (như full 61K Zalo Legal) | Khi cần pre-filtering phức tạp trên metadata hoặc đẩy lên Qdrant Server |

---

## 6. Khuyến Nghị Kiến Trúc Cho LuatCheck-D2 (Harness & Web Demo UI)

Dựa trên toàn bộ số liệu thực nghiệm trên, dưới đây là 3 khuyến nghị thiết thực nhất cho hệ thống `LuatCheck-D2`:

1. **Loại bỏ cấu hình `128-d`, sử dụng `768-d` làm chuẩn duy nhất khi bật Vector/Hybrid:**
   - Bản `768-d` vượt bản `128-d` tới **`+12.95%` `Recall@1`** và **`+14.67%` `Recall@5`** ở nhánh Vector, trong khi thời gian encode câu hỏi gần như tương đương và dung lượng đĩa trên cả 4 bộ cộng lại chỉ tốn **~`9.4 MB`** (với `NumPy` hoặc `FAISS Flat`).
2. **Chọn phương pháp truy hồi phù hợp với vai trò trong Pipeline:**
   - **Cho chế độ chạy nhanh / CPU-only / Không cần GPU (`hybrid_bm25`):** Giữ nguyên `LuatCheck BM25 + TF-IDF 1–3-gram RRF` hoặc `SQLite FTS5`. Cả hai có độ trễ chỉ `1.2–5.2 ms/query`, không tốn 517 MB VRAM cho model embedding, và đạt `MRR@10` từ `75.43%–80.20%` trên Zalo Legal (`94.44%–97.78%` trên các bộ luật chuyên biệt).
   - **Cho chế độ RAG / Agent (`hybrid_index` với `top_k = 8..20` đưa vào LLM đọc điều luật):** Sử dụng **`EmbeddingGemma-2 768-d Hybrid RRF (FTS5 + Vector 768-d)`** với backend `numpy` hoặc `faiss`, vì cấu hình này đạt **`Recall@20 = 99.39%`** trên Zalo Legal và **`Recall@10 = 100.0%`** trên `bll2019_v1` & `labour_vi_v1`.
3. **Đã triển khai mặc định Weighted RRF (`0.75 * FTS5 + 0.25 * Vector 768-d`) và bộ index `768-d` (`store: numpy`) trên toàn hệ thống:**
   - Trong [`src/indexing/hybrid.py`](../../src/indexing/hybrid.py), [`src/indexing/config.py`](../../src/indexing/config.py), [`src/config/app_config.py`](../../src/config/app_config.py) và [`src/retrieval/hybrid_domain.py`](../../src/retrieval/hybrid_domain.py), trọng số mặc định của `HybridSearcher` và `IndexedRetriever` đã được đặt thành `keyword_weight = 0.75`, `vector_weight = 0.25`.
   - Các profile cấu hình ([`demo-hcmut.yaml`](../../config/profiles/demo-hcmut.yaml), [`demo-labour.yaml`](../../config/profiles/demo-labour.yaml), [`demo-hcmut-gemma2-768d.yaml`](../../config/profiles/demo-hcmut-gemma2-768d.yaml), [`demo-labour-gemma2-768d.yaml`](../../config/profiles/demo-labour-gemma2-768d.yaml)) và target `make demo-web-gemma2` đã trỏ trực tiếp sang bộ index **`768-d`** (`store: numpy`).
