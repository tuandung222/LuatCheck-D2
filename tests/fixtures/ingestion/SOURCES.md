# Ingestion test fixtures: provenance

All text is real public legal text. Nothing here is synthetic.

| File | Content | Source |
|---|---|---|
| `labour_chuong1_dieu3_6.txt` | Chương I heading and Điều 3-6 of the Labour Code 2019 (clauses and points), original line wrapping kept | Official Gazette (Công báo số 993+994, 26-12-2019) PDF `docs/materials/benchmark-sources/bll2019-congbao.pdf`, via the page text in `docs/materials/benchmark-sources/bll2019-clean-pages.json` |
| `labour_dieu17_18.txt` | Chương III / Mục 1 headings and Điều 17-18 (Điều 17 has a heading wrapped over two lines) | same |
| `labour_chuong1_dieu1_2.md`, `.html`, `.docx` | Chương I heading, Điều 1 and Điều 2 as Markdown, HTML and Word, one paragraph per clause (line wraps of the PDF joined with a space) | same |

Notes on the non-text parts of the fixtures (they exist to exercise the loaders, they are not legal text):
the HTML file contains a `<style>` and a `<script>` element whose text must not appear in the output; the DOCX file contains a
three-row table listing the article numbers and titles of Điều 1-3 (to exercise table flattening).

The tests check that every fixture paragraph, whitespace-folded, occurs inside the corresponding record of the frozen corpus
`data/corpus/labor_code_2019_official.json`, so the fixtures cannot drift from the source.
