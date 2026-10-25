# Build the D2 slides: make -C deliverables/d2/slides   (or: make slides_d2 from the repository root)   (needs xelatex, pgfplots, fontspec with Arial and Menlo)
all: main.pdf

main.pdf: main.tex $(wildcard assets/*.png)
	xelatex -interaction=nonstopmode -halt-on-error main.tex
	xelatex -interaction=nonstopmode -halt-on-error main.tex

.PHONY: all main.pdf
