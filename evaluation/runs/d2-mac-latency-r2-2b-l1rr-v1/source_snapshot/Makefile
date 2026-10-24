PORT ?= 8501
HEADLESS ?= false
PYTHON ?= .venv/bin/python
WEB_PORT ?= 8000

.PHONY: prism-setup prism-server demo-model-server demo-model-server-2b demo-web-2b prism-server-gpu rerank-server-mac mlx-setup mlx-server test eval eval_d3 redteam demo web demo-web web-build report report_d2 report_d3 clean all

all: test report_d2

PRISM_DIR ?= $(HOME)/src/prism-llama.cpp
GGUF_REPO ?= prism-ml/Ternary-Bonsai-2-2B-gguf
GGUF_FILE ?= Ternary-Bonsai-2-2B-PQ2_0.gguf
PRISM_PORT ?= 8081
# D2 Mac latency run: PRISM_CTX=65536 (RUNBOOK) so one long trial has the same headroom as on the GPU server
PRISM_CTX ?= 32768

# Default model server: PrismML llama.cpp fork (ternary kernels), built from source with Metal.
prism-setup:
	[ -d $(PRISM_DIR) ] || git clone --depth 1 -b prism https://github.com/PrismML-Eng/llama.cpp $(PRISM_DIR)
	cmake -S $(PRISM_DIR) -B $(PRISM_DIR)/build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
	cmake --build $(PRISM_DIR)/build -j --target llama-server
	.venv-mlx/bin/hf download $(GGUF_REPO) $(GGUF_FILE) SHA256SUMS

prism-server:
	$(PRISM_DIR)/build/bin/llama-server \
	  -m "$$(.venv-mlx/bin/python -c 'from huggingface_hub import hf_hub_download as d; print(d("$(GGUF_REPO)", "$(GGUF_FILE)"))')" \
	  -ngl 99 -fa on -c $(PRISM_CTX) --host 127.0.0.1 --port $(PRISM_PORT) --alias $(GGUF_REPO) --jinja \
	  --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64

# Controller of the chosen D2 system (r2, Bonsai 4B) for the demo and the Mac latency run: same target, 4B GGUF.
demo-model-server:
	$(MAKE) prism-server GGUF_REPO=prism-ml/Ternary-Bonsai-2-4B-gguf GGUF_FILE=Ternary-Bonsai-2-4B-PQ2_0.gguf PRISM_CTX=65536

# Same chosen system with the lighter Bonsai 2B controller, on its own port so both demos can run side by side.
demo-model-server-2b:
	$(MAKE) prism-server PRISM_PORT=8083 PRISM_CTX=65536

demo-web-2b:
	@curl -sf -m 2 127.0.0.1:8083/health >/dev/null || echo "WARNING: 2B controller not healthy on 127.0.0.1:8083 (make demo-model-server-2b)"
	$(MAKE) demo-web DEMO_CONFIGS=config/profiles/demo-hcmut-2b.yaml,config/profiles/demo-labour-2b.yaml WEB_PORT=8001 DEMO_WEB_DB=data/db/web_demo_2b.sqlite3

# D2 GPU server (server 82): same PrismML llama.cpp commit and same GGUF as the Mac, built with CUDA (docs/RUNBOOK_D2.md).
#   make prism-server-gpu GPU=2 GPU_PORT=28081 NP=8 GGUF_PATH=/path/to/Ternary-Bonsai-2-2B-PQ2_0.gguf
# -np slots x CTX_PER_SLOT context (unified KV: the pool is shared, so give it headroom: 16384 per slot); the runner (profile gpu-accuracy) uses one worker per slot. Foreground: run it in tmux/nohup.
GPU ?= 0
# server 82 is shared: 8081/8082 may belong to others, so the GPU server uses an uncommon port (loopback only)
GPU_PORT ?= 28081
NP ?= 8
CTX_PER_SLOT ?= 16384
GGUF_PATH ?=
prism-server-gpu:
	@test -n "$(GGUF_PATH)" || { echo "set GGUF_PATH=/path/to/$(GGUF_FILE)"; exit 2; }
	@if (command -v ss >/dev/null && ss -ltnH "sport = :$(GPU_PORT)" | grep -q .) || (command -v lsof >/dev/null && lsof -nP -iTCP:$(GPU_PORT) -sTCP:LISTEN -t | grep -q .); then \
	  echo "port $(GPU_PORT) is already in use; pick another GPU_PORT (never reuse or kill someone else's server)"; exit 4; fi
	CUDA_VISIBLE_DEVICES=$(GPU) $(PRISM_DIR)/build/bin/llama-server \
	  -m "$(GGUF_PATH)" -ngl 99 -fa on -c $$(( $(NP) * $(CTX_PER_SLOT) )) -np $(NP) --kv-unified --host 127.0.0.1 --port $(GPU_PORT) \
	  --alias $(GGUF_REPO) --jinja \
	  --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64

# D2 Mac latency run: the llama.cpp reranker server (GGUF f16 of the pinned Vietnamese reranker; scripts/reranker/, docs/plans/reranker.md).
# Port rules (docs/RUNBOOK_D2.md A0): never start on a port anyone is already using, never reuse or kill a server that is not yours.
RERANKER_QUANT ?= f16
RERANKER_PORT ?= 8082
rerank-server-mac:
	@if (command -v lsof >/dev/null && lsof -nP -iTCP:$(RERANKER_PORT) -sTCP:LISTEN -t | grep -q .) || (command -v ss >/dev/null && ss -ltnH "sport = :$(RERANKER_PORT)" | grep -q .); then \
	  echo "port $(RERANKER_PORT) is already in use (a reranker server may already be running: check with curl -s 127.0.0.1:$(RERANKER_PORT)/health); not starting another"; exit 4; fi
	LLAMA_SERVER=$(PRISM_DIR)/build/bin/llama-server RERANKER_PORT=$(RERANKER_PORT) scripts/reranker/serve_mac.sh $(RERANKER_QUANT)

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

# D2 live demo: both demo profiles (HCMUT + labour) in one process with a corpus switch in the UI.
# Needs the controller (make prism-server) and reranker (make rerank-server-mac) servers; it only warns if they are down,
# because a run then shows an execution error by design (no fallback answer).
DEMO_CONFIGS ?= config/profiles/demo-hcmut.yaml,config/profiles/demo-labour.yaml
DEMO_WEB_DB ?= data/db/web_demo.sqlite3
demo-web:
	@test -f frontend/dist/index.html || npm --prefix frontend run build
	@curl -sf -m 2 127.0.0.1:8081/health >/dev/null || echo "WARNING: controller server not healthy on 127.0.0.1:8081 (make prism-server)"
	@curl -sf -m 2 127.0.0.1:8082/health >/dev/null || echo "WARNING: reranker server not healthy on 127.0.0.1:8082 (make rerank-server-mac)"
	LUATCHECK_WEB_CONFIGS=$(DEMO_CONFIGS) LUATCHECK_WEB_DB=$(DEMO_WEB_DB) LUATCHECK_WEB_PORT=$(WEB_PORT) PYTHONPATH=. $(PYTHON) -m src.api.app

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
        benchmark-status benchmark-compare benchmark-compare-systems judge tables audit-score

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
benchmark-d2-gpu: D2_EXTRA += --endpoint http://127.0.0.1:$(GPU_PORT)/v1
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

# Same-task comparison of systems (v3 vs the post-hoc revision r2, 2B vs 4B), paired bootstrap, md + tex + json under evaluation/comparisons/:
#   make benchmark-compare-systems ARMS="v3-2B=d2-gpu-main-hcmut-v3,d2-gpu-main-labour-v3 r2-2B=d2-gpu-r2-2b-hcmut-v1,d2-gpu-r2-2b-labour-v1 r2-4B=d2-gpu-r2-4b-hcmut-v1,d2-gpu-r2-4b-labour-v1"
ARMS ?=
benchmark-compare-systems:
	$(PYTHON) evaluation/run_d2.py compare $(foreach a,$(ARMS),--arm $(a)) $(D2_EXTRA)

judge:
	$(PYTHON) evaluation/run_d2.py judge --run-dir $(RUN) --execute $(D2_EXTRA)

tables:
	$(PYTHON) evaluation/run_d2.py tables --run-dir $(RUN)

audit-score:
	$(PYTHON) evaluation/score_benchmark_audit.py --run-dir $(RUN) --labels $(LABELS)

# ---- experiment tracking (docs/RUNBOOK_D2.md, docs/plans/benchmarking.md): which run, commit and harness produced which result, and is it current?
.PHONY: runs report-check stamp-provenance
runs:
	$(PYTHON) evaluation/run_d2.py registry

report-check: runs
	$(PYTHON) evaluation/check_report_provenance.py --report report_d2/main_d2.tex

# On a clean, pushed checkout that will be copied to a host without .git (server 82): certify it for main runs.
stamp-provenance:
	$(PYTHON) evaluation/run_d2.py stamp
