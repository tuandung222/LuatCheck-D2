# Course deliverables

Everything that is handed in for the course (CO5151) lives under this folder, one subfolder per deliverable. Code, data and run artifacts are elsewhere in the repository (`src/`, `evaluation/`, `data/`).

## Submitted for D2

| Deliverable | File |
|---|---|
| D2 interim report | [`d2/report/main_d2.pdf`](d2/report/main_d2.pdf) |
| D2 slides | [`d2/slides/main.pdf`](d2/slides/main.pdf) |

## Layout

| Folder | Content |
|---|---|
| `d1/report/` | D1 proposal (`main_d1.tex`, `main_d1.pdf`, `chap1.tex`) and the one-page version (`main_1page.*`). Historical, as submitted. |
| `d1/slides/` | D1 pitch deck (`LuatCheck_D1_Pitch.pptx`, `.pdf`) and speaker notes. Historical, as submitted. |
| `d2/report/` | D2 report: `main_d2.tex`, `refs.bib`, `images/`, generated result tables (`tables_*`, `appendix_plain/`, `benchmark_latency_mac.tex`), `RESULTS_PROVENANCE.md` (table to run to commit), and the table helper scripts `make_latency_table.py`, `plain_appendix.py`. |
| `d2/slides/` | D2 slides: `main.tex` (XeLaTeX, 16 pages), `assets/` (screenshots), `SPEAKER_NOTES.md`, `SOURCES_INTERNAL.md` (where each slide number comes from). |
| `d2/demo/` | Live-demo material: `DEMO_SCRIPT.md`, `D2_SLIDES_OUTLINE.md`, `demo_scenarios*.json`, `record_demo.py`, and `gifs/` (recordings and the backup videos `demo_backup*.mp4`). |
| `d3/report/` | Retired D3 draft, marked historical and not current evidence (see its README). |

## Build (from the repository root)

| Target | Command | Output |
|---|---|---|
| D2 report | `make report_d2` (pdflatex, bibtex, pdflatex, pdflatex) | `d2/report/main_d2.pdf` |
| D2 slides | `make slides_d2` (XeLaTeX, needs fonts Arial and Menlo; add `-B` to force a rebuild: `make -B slides_d2`) | `d2/slides/main.pdf` |
| D1 report | `make report_d1` | `d1/report/main_d1.pdf` |
| D3 draft | `make report_d3` | `d3/report/main_d3.pdf` |
| Report provenance check | `make report-check` (also lists the freshness of every run; rewrites `d2/report/RESULTS_PROVENANCE.md`) | exit code 0 = every result table comes from a current or pinned main run |

The D2 demo is started with `make demo-web` (see `d2/demo/DEMO_SCRIPT.md`); all numbers in the report are reproduced step by step in [`../docs/REPRODUCE_D2.md`](../docs/REPRODUCE_D2.md).
