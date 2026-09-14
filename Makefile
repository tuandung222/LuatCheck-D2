PORT ?= 8501
HEADLESS ?= false

.PHONY: test eval eval_d3 redteam demo report report_d2 report_d3 clean all

all: test eval_d3 redteam report

test:
	PYTHONPATH=. pytest tests/ -v

eval: eval_d3

eval_d3:
	PYTHONPATH=. python3 evaluation/run_eval.py --tasks evaluation/tasks/vlqa_full_20.json --seeds 42 123 2026 --ablation three_way --offline

redteam:
	PYTHONPATH=. python3 redteam/run_redteam.py

demo:
	streamlit run src/ui/app.py --server.port $(PORT) --server.headless $(HEADLESS) --browser.gatherUsageStats false

report: report_d2 report_d3

report_d2:
	rm -f report_d2/*.aux report_d2/*.bbl report_d2/*.blg report_d2/*.out report_d2/*.log report_d2/*.run.xml report_d2/*-blx.bib
	cd report_d2 && pdflatex -interaction=nonstopmode main_d2.tex && bibtex main_d2 && pdflatex -interaction=nonstopmode main_d2.tex && pdflatex -interaction=nonstopmode main_d2.tex

report_d3:
	rm -f report_d3/*.aux report_d3/*.bbl report_d3/*.blg report_d3/*.out report_d3/*.log report_d3/*.run.xml report_d3/*-blx.bib
	cd report_d3 && pdflatex -interaction=nonstopmode main_d3.tex && bibtex main_d3 && pdflatex -interaction=nonstopmode main_d3.tex && pdflatex -interaction=nonstopmode main_d3.tex

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find report_d2 report_d3 -type f \( -name "*.aux" -o -name "*.log" -o -name "*.out" -o -name "*.bbl" -o -name "*.blg" \) -delete 2>/dev/null || true
