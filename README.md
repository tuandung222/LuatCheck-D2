# LuatCheck — D2 Interim Presentation Slides

Standalone Beamer slide deck (`main.tex` -> `main.pdf`) for **LuatCheck** (CO5151 Advanced Agentic AI, Group 8, HCMUT).

## Files
- `main.tex`: Beamer LaTeX source (16:10 aspect ratio, 14 main slides + 5 backup slides)
- `main.pdf`: Pre-compiled slide deck
- `proposal_presentation_script/`: Presentation scripts and speaker notes:
  - [`proposal_presentation_script/D2_PRESENTATION_SCRIPT_VI.md`](./proposal_presentation_script/D2_PRESENTATION_SCRIPT_VI.md): Full Vietnamese presentation script for all 14 main slides + 5 backup slides (A–E)
  - [`proposal_presentation_script/D2_SPEAKER_NOTES_EN.md`](./proposal_presentation_script/D2_SPEAKER_NOTES_EN.md): English speaker notes, timing, and Q&A notes
  - [`proposal_presentation_script/D2_LIVE_DEMO_SCRIPT.md`](./proposal_presentation_script/D2_LIVE_DEMO_SCRIPT.md): Live demo runbook, verified queries, and fallback checklist
  - [`proposal_presentation_script/D1_PROPOSAL_PITCH_SCRIPT_VI.md`](./proposal_presentation_script/D1_PROPOSAL_PITCH_SCRIPT_VI.md) & [`LuatCheck_D1_SpeakerNotes.pdf`](./proposal_presentation_script/LuatCheck_D1_SpeakerNotes.pdf): D1 3-minute proposal pitch scripts
- `assets/`: Figures, demo screenshots, HCMUT logo, and TikZ architecture diagram (`assets/architecture.tikz`)
- `Makefile`: Build target for `main.pdf`

## Build PDF Locally

### Prerequisites
A standard **TeX Live** (2024/2025) or **MacTeX** installation with:
- `xelatex`
- OpenType font packages: `plex` (`IBMPlexSans`, `IBMPlexMono`), `plex-math` (`IBMPlexMath-Regular.otf`), `unicode-math`
- LaTeX packages: `beamer`, `tikz`, `pgfplots`, `booktabs`, `tabularx`, `adjustbox`

### 1. Clone only the `slides` branch
```bash
git clone -b slides --single-branch https://github.com/tuandung222/LuatCheck-D2.git luatcheck-slides
cd luatcheck-slides
```

### 2. Compile with `make`
```bash
make
```
Or run `xelatex` directly (two passes for page numbers and references):
```bash
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

The compiled presentation will be written to `main.pdf`.
