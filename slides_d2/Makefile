# Build the D2 slides: make -C slides_d2   (needs xelatex, pgfplots, fontspec with Arial and Menlo)
all: main.pdf

main.pdf: main.tex $(wildcard assets/*.png)
	xelatex -interaction=nonstopmode -halt-on-error main.tex
	xelatex -interaction=nonstopmode -halt-on-error main.tex

.PHONY: all
