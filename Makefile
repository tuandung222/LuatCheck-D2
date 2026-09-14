.PHONY: test eval redteam demo report all

all: test eval redteam report

test:
	PYTHONPATH=. pytest tests/ -v

eval:
	PYTHONPATH=. python3 evaluation/run_eval.py --seeds 42 123 2026 --ablation both

redteam:
	PYTHONPATH=. python3 redteam/run_redteam.py

demo:
	streamlit run src/ui/app.py

report:
	cd report_d2 && pdflatex -interaction=nonstopmode main_d2.tex && bibtex main_d2 && pdflatex -interaction=nonstopmode main_d2.tex && pdflatex -interaction=nonstopmode main_d2.tex
