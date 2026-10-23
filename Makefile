PORT ?= 8501
HEADLESS ?= false
PYTHON ?= .venv/bin/python
WEB_PORT ?= 8000

.PHONY: prism-setup prism-server mlx-setup mlx-server test eval eval_d3 redteam demo web web-build report report_d2 report_d3 clean all

all: test report_d2

PRISM_DIR ?= $(HOME)/src/prism-llama.cpp
GGUF_REPO ?= prism-ml/Ternary-Bonsai-2-2B-gguf
GGUF_FILE ?= Ternary-Bonsai-2-2B-PQ2_0.gguf
PRISM_PORT ?= 8081

# Default model server: PrismML llama.cpp fork (ternary kernels), built from source with Metal.
prism-setup:
	[ -d $(PRISM_DIR) ] || git clone --depth 1 -b prism https://github.com/PrismML-Eng/llama.cpp $(PRISM_DIR)
	cmake -S $(PRISM_DIR) -B $(PRISM_DIR)/build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
	cmake --build $(PRISM_DIR)/build -j --target llama-server
	.venv-mlx/bin/hf download $(GGUF_REPO) $(GGUF_FILE) SHA256SUMS

prism-server:
	$(PRISM_DIR)/build/bin/llama-server \
	  -m "$$(.venv-mlx/bin/python -c 'from huggingface_hub import hf_hub_download as d; print(d("$(GGUF_REPO)", "$(GGUF_FILE)"))')" \
	  -ngl 99 -fa on -c 32768 --host 127.0.0.1 --port $(PRISM_PORT) --alias $(GGUF_REPO) --jinja \
	  --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64

MLX_PYTHON ?= .venv-mlx/bin/python
MLX_MODEL ?= prism-ml/Ternary-Bonsai-2-2B-mlx-2bit
MLX_PORT ?= 8080

mlx-setup:
	uv venv .venv-mlx --python 3.12
	uv pip install --python $(MLX_PYTHON) "mlx-vlm>=0.7.8"
	.venv-mlx/bin/hf download $(MLX_MODEL)

mlx-server:
	$(MLX_PYTHON) -m mlx_vlm.server --model $(MLX_MODEL) --host 127.0.0.1 --port $(MLX_PORT)

test:
	PYTHONPATH=. $(PYTHON) -m pytest tests/ -v

eval: eval_d3

eval_d3:
	@echo "No automatic experiments. See report_d2/D2_EXPERIMENT_PLAN.md for explicit native collection commands."

redteam:
	@echo "Legacy red-team scorer is disabled. Threat-model review is in report_d2/D2_EXPERIMENT_PLAN.md."

demo:
	streamlit run src/ui/app.py --server.port $(PORT) --server.headless $(HEADLESS) --browser.gatherUsageStats false

web:
	LUATCHECK_WEB_PORT=$(WEB_PORT) PYTHONPATH=. $(PYTHON) -m src.api.app

web-build:
	npm --prefix frontend run build

report: report_d2 report_d3

report_d2:
	cd report_d2 && \
	rm -f *.aux *.bbl *.blg *.out *.log *.run.xml *-blx.bib *.toc *.lot *.lof && \
	pdflatex -interaction=nonstopmode main_d2.tex && \
	bibtex main_d2 && \
	pdflatex -interaction=nonstopmode main_d2.tex && \
	pdflatex -interaction=nonstopmode main_d2.tex

report_d3:
	cd report_d3 && \
	rm -f *.aux *.bbl *.blg *.out *.log *.run.xml *-blx.bib *.toc *.lot *.lof && \
	pdflatex -interaction=nonstopmode main_d3.tex && \
	bibtex main_d3 && \
	pdflatex -interaction=nonstopmode main_d3.tex && \
	pdflatex -interaction=nonstopmode main_d3.tex

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find report_d2 report_d3 -type f \( -name "*.aux" -o -name "*.log" -o -name "*.out" -o -name "*.bbl" -o -name "*.blg" -o -name "*.run.xml" -o -name "*-blx.bib" -o -name "*.toc" -o -name "*.lot" -o -name "*.lof" \) -delete 2>/dev/null || true

# ---- D2 benchmarking: evaluation/run_benchmark.py, judge_benchmark.py, render_benchmark_tables.py (docs/plans/benchmarking.md)
# `make benchmark-d2` runs the 2 official benchmarks x 3 variants x 3 seeds on real inference, judges, and renders
# report_d2/benchmark_results.tex. It never starts a model server (see `make prism-server`).
.PHONY: benchmark-freeze benchmark-d2 benchmark-smoke

RUN_PROFILE ?= mac-latency
BENCHMARKS ?= all
BENCH_VARIANTS ?= off,l1,l1_rerank
BENCH_SEEDS ?= 42 123 2026
BENCH_MODEL ?= config/benchmark/model_prism_gguf2b.yaml
BENCH_STAMP := $(shell date +%Y%m%d-%H%M%S)
BENCH_OUT ?= evaluation/runs/d2-$(RUN_PROFILE)-$(BENCH_STAMP)
BENCH_EXTRA ?=
SMOKE_BENCHMARKS ?= hcmut_v1
SMOKE_VARIANTS ?= off,l1
SMOKE_OUT ?= evaluation/runs/bench-smoke-$(BENCH_STAMP)
bench_args = $(foreach b,$(1),--benchmark $(b))
bench_comma := ,
bench_empty :=
bench_space := $(bench_empty) $(bench_empty)

benchmark-freeze:
	$(PYTHON) evaluation/run_benchmark.py freeze $(call bench_args,$(BENCHMARKS))

benchmark-d2: benchmark-freeze
	$(PYTHON) evaluation/run_benchmark.py run $(call bench_args,$(BENCHMARKS)) --variants $(BENCH_VARIANTS) \
	  --seeds $(BENCH_SEEDS) --run-profile $(RUN_PROFILE) --model-config $(BENCH_MODEL) --output $(BENCH_OUT) --execute $(BENCH_EXTRA)
	$(PYTHON) evaluation/judge_benchmark.py all --run-dir $(BENCH_OUT) --execute
	$(PYTHON) evaluation/render_benchmark_tables.py --run-dir $(BENCH_OUT) --output report_d2/benchmark_results.tex

# Pipeline check on a few tasks, one seed; never writes report_d2 and the run is marked non-eligible.
benchmark-smoke:
	$(PYTHON) evaluation/run_benchmark.py run $(call bench_args,$(SMOKE_BENCHMARKS)) --variants $(SMOKE_VARIANTS) \
	  --seeds 42 --limit 3 --allow-unfrozen --run-profile $(RUN_PROFILE) --model-config $(BENCH_MODEL) --output $(SMOKE_OUT) --execute
	$(PYTHON) evaluation/judge_benchmark.py all --run-dir $(SMOKE_OUT) --execute
	$(PYTHON) evaluation/render_benchmark_tables.py --run-dir $(SMOKE_OUT) --output $(SMOKE_OUT)/analysis/benchmark_results.tex \
	  --allow-non-eligible --expect-benchmarks $(subst $(bench_space),$(bench_comma),$(strip $(SMOKE_BENCHMARKS))) --expect-variants $(SMOKE_VARIANTS)
