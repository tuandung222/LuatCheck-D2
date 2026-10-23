# Labour-law sources (labour_vi v1)

Scope: ten official Vietnamese labour and employment documents, one per DOCCODE, used to build the second benchmark corpus `data/corpus/labour_vi_v1.json` (458 records). The first document is the 2019 Labour Code, included as-is. The other nine are limited to 40 pages each.

Build: `PYTHONPATH=. .venv/bin/python -I -m src.ingestion build --config config/ingestion/labour_vi_v1.yaml` (status `ok`; `--check` reports "up to date"). Config: `config/ingestion/labour_vi_v1.yaml`. Machine-readable provenance: `manifest.json` in this folder. Build manifest: `data/corpus/labour_vi_v1.manifest.json`.

## Included documents

Retrieval times are UTC. Dates are as printed in the PDF. For laws, the printed date is the adoption date ("thông qua ngày"). Page counts come from pypdf. Coverage is the share of non-whitespace source characters that fall inside a record.

| DOCCODE | Title (short) | Number | Issued / adopted | Effective (printed) | Pages | Records | Coverage | Source URL (congbao.chinhphu.vn PDF) |
|---|---|---|---|---|---|---|---|---|
| BLLD2019 | Bộ luật Lao động 2019 | 45/2019/QH14 | 20-11-2019 (adopted) | 01-01-2021 | 94 (exception) | 220 | 98.8% | congbaocdn.../2019/11/30232/29070-1-2019993-99445-2019-qh14.pdf |
| LVL2025 | Luật Việc làm | 74/2025/QH15 | 16-06-2025 (adopted) | 01-01-2026 | 27 | 55 | 98.2% | congbaocdn.../2025/6/45562/57700-1-2025967-96874-2025-qh15.pdf |
| ND293_2025 | Mức lương tối thiểu (hợp đồng lao động) | 293/2025/NĐ-CP | 10-11-2025 | 01-01-2026 | 17 | 5 | 22.2% (annex missing) | congbaocdn.../2025/11/46568/59713-1-20251591-1592293-2025-nd-cp.pdf |
| ND318_2025 | Đăng ký lao động, hệ thống thông tin thị trường lao động | 318/2025/NĐ-CP | 12-12-2025 | 01-01-2026 | 24 | 25 | 68.6% (forms annex missing) | congbaocdn.../2025/12/46804/60300-1-20251717-1718318-2025-nd-cp.pdf |
| ND219_2025 | Người lao động nước ngoài làm việc tại Việt Nam | 219/2025/NĐ-CP | 07-08-2025 | 07-08-2025 | 36 | 36 | 73.1% (forms annex missing) | congbaocdn.../2025/8/45798/58141-1-20251073-1074219-2025-nd-cp.pdf |
| LCD2024 | Luật Công đoàn | 50/2024/QH15 | 27-11-2024 (adopted) | 01-07-2025 | 25 | 37 | 98.7% | congbaocdn.../2024/11/43589/53742-1-20241533-153450-2024-qh15.pdf |
| ND135_2020 | Tuổi nghỉ hưu | 135/2020/NĐ-CP | 18-11-2020 | 01-01-2021 | 17 | 12 | 96.0% | congbaocdn.../2020/11/32525/33432-1-20201117-1118135-2020-nd-cp.pdf |
| ND274_2025 | Chậm đóng, trốn đóng BHXH, BHTN; khiếu nại BHXH | 274/2025/NĐ-CP | 16-10-2025 | 30-11-2025 | 14 | 16 | 91.9% | congbaocdn.../2025/10/46418/59403-1-20251515-1516274-2025-nd-cp.pdf |
| ND143_2024 | BHTNLĐ tự nguyện (người lao động không theo hợp đồng) | 143/2024/NĐ-CP | 01-11-2024 | 01-01-2025 | 35 | 47 | 94.1% | congbaocdn.../2024/11/43119/52597-1-20241249-1250143-2024-nd-cp.pdf |
| TT26_2025 | Danh mục vùng KT-XH đặc biệt khó khăn (nghỉ hưu sớm) | **not printed** | **not printed** | 01-01-2026 (Điều 4.1) | 7 | 5 | 31.9% (annex missing) | datafiles.chinhphu.vn/cpp/files/vbpq/2025/12/26-bnv.pdf (attachment of vanban.chinhphu.vn docid 216367) |

Full URLs, file sizes, sha256 values and per-document checks are in `manifest.json`. Local copies are in this folder under the names `<DOCCODE>_<number>.pdf`, except BLLD2019, which stays at `docs/materials/benchmark-sources/bll2019-congbao.pdf`.

Totals: 458 records (446 article records and 12 section records for the appendices). Article numbering has no gaps in any document. The build found no duplicate ids after the fix described under "Caveats".

## Why these are official

Every PDF comes from `congbao.chinhphu.vn` (Công báo điện tử of the Government, the official gazette) or from the official attachment on `vanban.chinhphu.vn` (TT26). The gazette issue appears in the header of each Công báo PDF (not in the TT26 copy). Only official hosts were used. Commercial sites were not used. The vbpl.vn database (`vbpl.vn`) was used only to check status and was not used as a text source, because its pages are rendered in the browser and curl returns no text.

## Amendment and status relationships (checked in the printed text)

- LVL2025 repeals Luật Việc làm 38/2013/QH13 (as amended by 41/2024/QH15). Its implementing decrees 318/2025 are included; 338/2025 and 352/2025 are not (page limit).
- LCD2024 (Điều 37) repeals Luật Công đoàn 12/2012/QH13.
- ND293_2025 (Điều 5.2) repeals NĐ 74/2024/NĐ-CP.
- ND219_2025 succeeds NĐ 152/2020/NĐ-CP for foreign workers in Vietnam. Điều 34 keeps permits issued under 152/2020 valid until expiry. The printed text also ends the NĐ 70/2023 amendments on Vietnamese workers for foreign organisations.
- ND135_2020 (Điều 8.2) repeals listed provisions of NĐ 115/2015/NĐ-CP and NĐ 134/2015/NĐ-CP.
- ND143_2024 is a separate voluntary scheme. It does not replace the compulsory scheme in NĐ 88/2020/NĐ-CP, which is not included.
- TT26_2025 (Điều 4.2) repeals Thông tư 19/2021/TT-BLĐTBXH, which is not included.
- Later amendments were not checked for any document. Status is "as printed in this PDF", not a consolidated current text.

## Caveats

1. **Appendices after the signature are mostly not captured.** The `vi_legal` ruleset only recognises numbered appendices ("Phụ lục I"). Unnumbered annexes after "TM. CHÍNH PHỦ" are uncovered. Consequences:
   - ND293_2025: the Phụ lục listing localities by wage region (about 17,100 non-whitespace characters, 76% of the document's text) is not in the corpus. The corpus holds only Điều 1-5, which is the wage rule but not the list.
   - TT26_2025: the Danh mục of regions is not in the corpus. Only Điều 1-5 are present (about 32% coverage).
   - ND318_2025, ND219_2025, ND274_2025: form annexes after the signature are not in the corpus. This is minor for the operative text.
2. **TT26_2025 is unverified.** The PDF on `datafiles.chinhphu.vn` prints "Số: /2025/TT-BNV" and a blank date. It may be an unsigned copy. The date 29-12-2025 and the signatory come from a search summary of the vanban.chinhphu.vn page, which was not opened. Check it against the signed text before using it.
3. **ND143_2024 sample articles.** Phụ lục III of the decree contains a sample decision with its own Điều 1-3. Those three articles carry the series tag `MAU_`, so their ids are `ND143_2024_MAU_Dieu_1` to `_3`. This deviates from the `<DOCCODE>_Dieu_<n>` format, which the pipeline cannot produce for a second series without the tag. The decree's own articles are `ND143_2024_Dieu_1` to `_35`. Exclude `MAU_` ids from article-level tasks.
4. **BLLD2019 page 94** has no text layer and contributes nothing (pipeline warning). The article content matches the frozen `labor_code_2019_official.json` for all 220 articles.
5. **Warnings with no effect on the corpus.** The pipeline kept some clause or point lines in forms and tables as ordinary text (for example "1. Thành phố Hà Nội" in the ND293 annex). These lines are in the affected article text, not dropped.

## Rejected candidates

Downloaded and measured, then rejected for the 40-page limit or because they were replaced. Full list with URLs in `manifest.json` (`rejected_candidates`).

- Over 40 pages: Luật BHXH 41/2024 (88), NĐ 145/2020 (95, the core implementing decree of the Labour Code: largest gap), NĐ 12/2022 (95, replaced by NĐ 283/2026), NĐ 283/2026 (100, current penalty decree; a page-limit exception would be needed), NĐ 352/2025 (55), NĐ 338/2025 (42), NĐ 158/2025 (60), NĐ 152/2020 (61), Luật 69/2020 on overseas workers (45), Luật ATVSLD 84/2015 (56), TT 21/2021 (68), NĐ 88/2020 (67).
- Replaced or repealed: NĐ 74/2024 (by NĐ 293/2025), Luật Công đoàn 12/2012, Luật Việc làm 38/2013, TT 19/2021 (13 pages, by TT 26/2025), NĐ 70/2023 (amends NĐ 152/2020).
- Not obtained: NĐ 39/2016/NĐ-CP (the PDF host failed the TLS check, so the file was not downloaded; status not verified), NĐ 37/2016 (listed as expired on vbpl, not downloaded), TT 12/2025/TT-BNV (no official PDF found).

## Unverified items

- TT26_2025 number, issue date and signatory (see caveat 2).
- Amendment or replacement after the printed dates, for every document.
- BLLD2019 retrieval time (existing file, not recorded in `corpus_manifest.json`).
