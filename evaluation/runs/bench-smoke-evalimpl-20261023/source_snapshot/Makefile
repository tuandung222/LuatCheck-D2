PORT ?= 8501
HEADLESS ?= false
PYTHON ?= .venv/bin/python
WEB_PORT ?= 8000

.PHONY: prism-setup prism-server prism-server-gpu rerank-server-mac mlx-setup mlx-server test eval eval_d3 redteam demo web web-build report report_d2 report_d3 clean all

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

# D2 GPU server (server 82): same PrismML llama.cpp commit and same GGUF as the Mac, built with CUDA (docs/RUNBOOK_D2.md).
#   make prism-server-gpu GPU=1 PRISM_PORT=8081 NP=8 GGUF_PATH=/path/to/Ternary-Bonsai-2-2B-PQ2_0.gguf
# -np slots x 8192 context per slot; the runner (profile gpu-accuracy) uses one worker per slot. Foreground: run it in tmux/nohup.
GPU ?= 0
NP ?= 8
CTX_PER_SLOT ?= 8192
GGUF_PATH ?=
prism-server-gpu:
	@test -n "$(GGUF_PATH)" || { echo "set GGUF_PATH=/path/to/$(GGUF_FILE)"; exit 2; }
	CUDA_VISIBLE_DEVICES=$(GPU) $(PRISM_DIR)/build/bin/llama-server \
	  -m "$(GGUF_PATH)" -ngl 99 -fa on -c $$(( $(NP) * $(CTX_PER_SLOT) )) -np $(NP) --host 127.0.0.1 --port $(PRISM_PORT) \
	  --alias $(GGUF_REPO) --jinja \
	  --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64

# D2 Mac latency run: the llama.cpp reranker server on 127.0.0.1:8082 (Vietnamese reranker GGUF; see scripts/reranker/).
RERANKER_QUANT ?= Q8_0
rerank-server-mac:
	LLAMA_SERVER=$(PRISM_DIR)/build/bin/llama-server RERANKER_QUANT=$(RERANKER_QUANT) scripts/reranker/serve_mac.sh

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

# ---- D2 benchmarking: evaluation/run_d2.py drives run_benchmark.py, judge_benchmark.py, render_benchmark_tables.py
# (docs/plans/benchmarking.md, docs/RUNBOOK_D2.md). It never starts a model server (see prism-server / prism-server-gpu /
# rerank-server-mac). All matrix/variant/profile choices are config: config/benchmark/{d2_matrix,variants,profile_*}.yaml.
#
#   make benchmark-d2-gpu                       # on server 82:   2 benchmarks x 3 variants x 3 seeds, profile gpu-accuracy
#   make benchmark-d2-mac                       # on the Mac:     same matrix, profile mac-latency (sequential, reportable latency)
#   make benchmark-d2-gpu RUN_ID=<existing>     # RESUME: same RUN_ID = same run directory (append only)
#   make benchmark-smoke                        # 3 tasks, 1 seed, both benchmarks, off+l1: pipeline check, never report evidence
#   make judge RUN=evaluation/runs/<id>         # judge stage alone (needs the gateway key on this machine)
#   make tables RUN=evaluation/runs/<id>        # analysis + tables + RUN_NOTES alone
.PHONY: benchmark-freeze benchmark-preflight benchmark-d2 benchmark-d2-gpu benchmark-d2-mac benchmark-smoke \
        benchmark-status benchmark-compare judge tables audit-score

RUN_PROFILE ?= mac-latency
BENCH_STAMP := $(shell date +%Y%m%d-%H%M%S)
RUN_ID ?= d2-$(RUN_PROFILE)-$(BENCH_STAMP)
BENCH_OUT ?= evaluation/runs/$(RUN_ID)
D2_EXTRA ?=
RUN ?= $(BENCH_OUT)
SMOKE_BENCHMARKS ?= hcmut_v1 labour_vi_v1
SMOKE_VARIANTS ?= off,l1
SMOKE_LIMIT ?= 3
SMOKE_OUT ?= evaluation/runs/bench-smoke-$(BENCH_STAMP)
LABELS ?= $(RUN)/analysis/human-audit/labels.csv

benchmark-freeze:
	$(PYTHON) evaluation/run_benchmark.py freeze --benchmark all

benchmark-preflight:
	$(PYTHON) evaluation/run_d2.py preflight --profile $(RUN_PROFILE) $(D2_EXTRA)

benchmark-d2:
	$(PYTHON) evaluation/run_d2.py all --profile $(RUN_PROFILE) --run-dir $(BENCH_OUT) --execute $(D2_EXTRA)

benchmark-d2-gpu: RUN_PROFILE=gpu-accuracy
benchmark-d2-gpu: benchmark-d2

benchmark-d2-mac: RUN_PROFILE=mac-latency
benchmark-d2-mac: benchmark-d2

# Pipeline check on a few tasks, one seed; marked non-eligible, tables carry a red banner and cannot be published.
benchmark-smoke:
	$(PYTHON) evaluation/run_d2.py all --profile $(RUN_PROFILE) --benchmarks $(SMOKE_BENCHMARKS) --variants $(SMOKE_VARIANTS) \
	  --seeds 42 --limit $(SMOKE_LIMIT) --allow-unfrozen --run-dir $(SMOKE_OUT) --execute $(D2_EXTRA)

benchmark-status:
	$(PYTHON) evaluation/run_d2.py status --run-dir $(RUN)

benchmark-compare:
	$(PYTHON) evaluation/run_d2.py compare $(RUN_A) $(RUN_B)

judge:
	$(PYTHON) evaluation/run_d2.py judge --run-dir $(RUN) --execute $(D2_EXTRA)

tables:
	$(PYTHON) evaluation/run_d2.py tables --run-dir $(RUN)

audit-score:
	$(PYTHON) evaluation/score_benchmark_audit.py --run-dir $(RUN) --labels $(LABELS)
