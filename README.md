# LuatCheck — D2 Interim Presentation Slides

Standalone Beamer slide deck (`main.tex` -> `main.pdf`) for **LuatCheck** (CO5151 Advanced Agentic AI, Group 8, HCMUT).

## Files
- `main.tex`: Beamer LaTeX source (16:10 aspect ratio, 12 main slides + 4 backup slides)
- `main.pdf`: Pre-compiled slide deck
- `SPEAKER_NOTES.md`: 10-minute presentation script, timing, and Q&A notes
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
