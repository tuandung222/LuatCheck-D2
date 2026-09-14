.PHONY: test eval eval_d3 redteam demo report report_d2 report_d3 all

all: test eval_d3 redteam report

test:
	PYTHONPATH=. pytest tests/ -v

eval:
	PYTHONPATH=. python3 evaluation/run_eval.py --seeds 42 123 2026 --ablation both

eval_d3:
	PYTHONPATH=. python3 evaluation/run_eval.py --tasks evaluation/tasks/vlqa_full_20.json --seeds 42 123 2026 --ablation three_way

redteam:
	PYTHONPATH=. python3 redteam/run_redteam.py

demo:
	streamlit run src/ui/app.py

report: report_d2 report_d3

report_d2:
	cd report_d2 && pdflatex -interaction=nonstopmode main_d2.tex && bibtex main_d2 && pdflatex -interaction=nonstopmode main_d2.tex && pdflatex -interaction=nonstopmode main_d2.tex

report_d3:
	cd report_d3 && pdflatex -interaction=nonstopmode main_d3.tex && bibtex main_d3 && pdflatex -interaction=nonstopmode main_d3.tex && pdflatex -interaction=nonstopmode main_d3.tex
