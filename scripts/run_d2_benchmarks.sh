#!/usr/bin/env bash
# One entry point for the D2 benchmark matrix on a server or the Mac, safe to start inside tmux/nohup and to RE-RUN after a crash.
#
#   GPU (server 82):  CUDA_VISIBLE_DEVICES=1 GGUF_PATH=/home/dungvpt/models/Ternary-Bonsai-2-2B-PQ2_0.gguf PRISM_DIR=/home/dungvpt/src/prism-llama.cpp \
#                     scripts/run_d2_benchmarks.sh gpu
#   Mac (latency):    scripts/run_d2_benchmarks.sh mac
#
# What it does: checks the GPU is free (gpu) -> starts the llama-server for Bonsai if nothing healthy answers on $PRISM_PORT (the
# Mac also starts the reranker server on $RERANKER_PORT if absent) -> evaluation/run_d2.py all (preflight, collect, judge, analyze,
# tables, RUN_NOTES) -> stops ONLY the servers it started. Re-running with the same RUN_ID resumes the same run directory
# (append only; a drifted code/config/server is refused). Logs: logs/d2/$RUN_ID/{server.log,reranker.log,run.log,env.txt}.
#
# Environment (defaults in brackets)
#   RUN_ID            run directory name under evaluation/runs/            [d2-<profile>-main-v1]
#   CUDA_VISIBLE_DEVICES  GPU id for the server AND the torch reranker (gpu: required)
#   PRISM_DIR         llama.cpp (PrismML fork) checkout with build/bin/llama-server   [$HOME/src/prism-llama.cpp]
#   GGUF_PATH         the controller GGUF, Ternary-Bonsai-2-{2B,4B}-PQ2_0.gguf (needed only when this script has to start the server)
#   PRISM_PORT        controller server port (loopback only)              [gpu: 28081 - server 82 is shared, 8081/8082 may be taken by others; mac: 8081]
#   MODEL_CONFIG      controller model config passed to run_d2.py (--model-config)  [the matrix default, config/benchmark/model_prism_gguf2b.yaml]
#                     post-hoc revision r2: config/benchmark/model_prism_gguf2b_r2.yaml or ..._gguf4b_r2.yaml
#   MATRIX            collection matrix YAML (--matrix)                   [config/benchmark/d2_matrix.yaml]; post-hoc revision r2: config/benchmark/d2_matrix_r2.yaml
#                     (it carries `protocol: r2-posthoc`; the runner then tags the manifest, tables and RUN_NOTES)
#   MODEL_ALIAS       alias the started controller server serves (must equal model.name of the model config)  [model.name of MODEL_CONFIG, else
#                     prism-ml/Ternary-Bonsai-2-2B-gguf]; a value that differs from the config's model.name is refused (exit 2). The preflight pins the
#                     controller identity (GGUF sha256, quantisation) for that alias in config/benchmark/expected_server.yaml (2B top level, 4B under controllers:).
#   NP                server slots = runner workers (gpu)                  [8]   (-c = NP x CTX_PER_SLOT, CTX_PER_SLOT [16384])
#   MAC_CTX           mac server -c (unified KV, 4 slots; one sequence may use all of it)  [65536]
#   RERANKER_PORT     mac reranker server port                             [8082]
#   PYTHON            interpreter with the repo requirements               [.venv/bin/python, else python3]
#   SKIP_JUDGE=1      collect + tables only (no gateway key on this machine; judge later with `make judge RUN=...`)
#   MAX_JUDGE_USD     refuse the judge stage above this estimate           [config/benchmark/d2_matrix.yaml]
#   KEEP_SERVERS=1    do not stop servers this script started
#   MAX_GPU_USED_MB   refuse to start on a GPU with more memory in use    [4000]; FORCE_GPU=1 overrides
#   EXTRA             extra arguments for run_d2.py (e.g. "--limit 3 --allow-unfrozen" for a smoke run)
set -uo pipefail
cd "$(dirname "$0")/.."

KIND="${1:-${KIND:-}}"
case "$KIND" in
  gpu) PROFILE=gpu-accuracy ;;
  mac) PROFILE=mac-latency ;;
  *) echo "usage: $0 gpu|mac" >&2; exit 2 ;;
esac
RUN_ID="${RUN_ID:-d2-$PROFILE-main-v1}"
PRISM_DIR="${PRISM_DIR:-$HOME/src/prism-llama.cpp}"
if [ "$KIND" = gpu ]; then PRISM_PORT="${PRISM_PORT:-28081}"; else PRISM_PORT="${PRISM_PORT:-8081}"; fi
NP="${NP:-8}"
CTX_PER_SLOT="${CTX_PER_SLOT:-16384}"
RERANKER_PORT="${RERANKER_PORT:-8082}"
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi; fi
LOG_DIR="logs/d2/$RUN_ID"
mkdir -p "$LOG_DIR"
# The alias the server must serve is the model.name of the model config (MODEL_CONFIG, else the matrix default): derive it, and refuse a contradicting MODEL_ALIAS.
CONFIG_FOR_ALIAS="${MODEL_CONFIG:-}"
if [ -z "$CONFIG_FOR_ALIAS" ]; then
  CONFIG_FOR_ALIAS="$("$PYTHON" -c 'import sys,yaml;print((yaml.safe_load(open(sys.argv[1])) or {}).get("model_config",""))' "${MATRIX:-config/benchmark/d2_matrix.yaml}" 2>/dev/null || true)"
fi
CONFIG_ALIAS=""
if [ -n "$CONFIG_FOR_ALIAS" ] && [ -f "$CONFIG_FOR_ALIAS" ]; then
  CONFIG_ALIAS="$("$PYTHON" -c 'import sys,yaml;print(((yaml.safe_load(open(sys.argv[1])) or {}).get("model") or {}).get("name",""))' "$CONFIG_FOR_ALIAS" 2>/dev/null || true)"
fi
if [ -n "${MODEL_ALIAS:-}" ] && [ -n "$CONFIG_ALIAS" ] && [ "$MODEL_ALIAS" != "$CONFIG_ALIAS" ]; then
  echo "MODEL_ALIAS=$MODEL_ALIAS contradicts model.name=$CONFIG_ALIAS of $CONFIG_FOR_ALIAS: the server must serve the alias the config asks for." >&2; exit 2
fi
MODEL_ALIAS="${MODEL_ALIAS:-${CONFIG_ALIAS:-prism-ml/Ternary-Bonsai-2-2B-gguf}}"
STARTED_PIDS=()

log() { echo "$(date -u +%FT%TZ) [run_d2_benchmarks] $*" | tee -a "$LOG_DIR/run.log"; }
healthy() { curl -fsS -m 3 "http://127.0.0.1:$1/health" >/dev/null 2>&1; }
# Is anything (anyone) listening on the port?  ss/lsof see other users' sockets without their pid; /dev/tcp is the last resort.
port_in_use() {
  if command -v ss >/dev/null 2>&1; then ss -ltnH "sport = :$1" 2>/dev/null | grep -q . && return 0 || return 1; fi
  if command -v lsof >/dev/null 2>&1; then lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | grep -q . && return 0 || return 1; fi
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}
# pid(s) of a listener on the port that belongs to the CURRENT user (ss shows pids only for own processes; lsof -u filters on the user)
own_listener_pids() {
  if command -v lsof >/dev/null 2>&1; then lsof -a -nP -iTCP:"$1" -sTCP:LISTEN -u "$(id -un)" -t 2>/dev/null | sort -u
  elif command -v ss >/dev/null 2>&1; then ss -ltnpH "sport = :$1" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u; fi
}
require_own_server() {  # port label : abort unless a healthy llama-server of ours answers there
  local pids pid cmd
  pids="$(own_listener_pids "$1")"
  [ -n "$pids" ] || { log "$2 on port $1 answers /health but its process is NOT owned by user $(id -un): it is someone else's server. Refusing to use it. Choose another PRISM_PORT (RUNBOOK section A0)."; exit 4; }
  for pid in $pids; do
    cmd="$(ps -o command= -p "$pid" 2>/dev/null)"
    case "$cmd" in *llama-server*) return 0 ;; esac
  done
  log "$2 on port $1 is owned by this user but is not a llama-server ($cmd): refusing to use it."; exit 4
}
require_free_port() {  # port label : abort when anything listens there
  port_in_use "$1" && { log "port $1 ($2) is already in use (by someone else, or an unhealthy leftover). Not starting: pick another port (PRISM_PORT / RERANKER_PORT). This script never kills processes it did not start."; exit 4; }
  return 0
}
cleanup() {
  if [ "${KEEP_SERVERS:-0}" = "1" ]; then log "KEEP_SERVERS=1: leaving servers running: ${STARTED_PIDS[*]:-none}"; return; fi
  for pid in "${STARTED_PIDS[@]:-}"; do
    # only a pid this script started AND whose command line is still our llama-server (never a recycled pid, never someone else's process)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && ps -o command= -p "$pid" 2>/dev/null | grep -q "llama-server\|serve_mac.sh"; then
      log "stopping server pid $pid (started by this script)"; kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT
trap 'log "interrupted"; exit 130' INT TERM

wait_healthy() {  # port label
  for _ in $(seq 1 150); do healthy "$1" && return 0; sleep 2; done
  log "$2 did not become healthy on port $1 within 300 s (see $LOG_DIR)"; return 1
}

{
  echo "date: $(date -u +%FT%TZ)"; echo "host: $(hostname)"; echo "kind: $KIND profile: $PROFILE run_id: $RUN_ID"
  echo "PRISM_DIR=$PRISM_DIR PRISM_PORT=$PRISM_PORT NP=$NP CTX_PER_SLOT=$CTX_PER_SLOT RERANKER_PORT=$RERANKER_PORT"
  echo "MODEL_ALIAS=$MODEL_ALIAS MODEL_CONFIG=${MODEL_CONFIG:-matrix default} MATRIX=${MATRIX:-config/benchmark/d2_matrix.yaml}"
  echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset} GGUF_PATH=${GGUF_PATH:-unset} PYTHON=$PYTHON SKIP_JUDGE=${SKIP_JUDGE:-0}"
  echo "git: $(git rev-parse HEAD 2>/dev/null || echo none) dirty-files: $(git status --porcelain 2>/dev/null | wc -l)"
} >"$LOG_DIR/env.txt"

if [ "$KIND" = gpu ]; then
  [ -n "${CUDA_VISIBLE_DEVICES:-}" ] || { log "set CUDA_VISIBLE_DEVICES to a FREE GPU (shared server: check nvidia-smi)"; exit 2; }
  if command -v nvidia-smi >/dev/null; then
    used=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' -v g="${CUDA_VISIBLE_DEVICES%%,*}" '$1==g{print $2}')
    log "GPU ${CUDA_VISIBLE_DEVICES}: ${used:-?} MiB in use"
    if [ -n "$used" ] && [ "$used" -gt "${MAX_GPU_USED_MB:-4000}" ] && [ "${FORCE_GPU:-0}" != "1" ] && ! { healthy "$PRISM_PORT" && [ -n "$(own_listener_pids "$PRISM_PORT")" ]; }; then
      log "GPU ${CUDA_VISIBLE_DEVICES} is not free (> ${MAX_GPU_USED_MB:-4000} MiB used by others). Pick another GPU or FORCE_GPU=1."; exit 2
    fi
  fi
fi

# --- controller server
if healthy "$PRISM_PORT"; then
  require_own_server "$PRISM_PORT" "controller server"
  log "controller server already healthy on $PRISM_PORT and owned by $(id -un): reusing it (not stopped by this script)"
else
  require_free_port "$PRISM_PORT" "controller server"
  [ -n "${GGUF_PATH:-}" ] && [ -f "$GGUF_PATH" ] || { log "no healthy server on $PRISM_PORT and GGUF_PATH is not a file; cannot start one"; exit 2; }
  [ -x "$PRISM_DIR/build/bin/llama-server" ] || { log "missing $PRISM_DIR/build/bin/llama-server (build it: docs/RUNBOOK_D2.md)"; exit 2; }
  if [ "$KIND" = gpu ]; then SLOTS="-np $NP -c $((NP * CTX_PER_SLOT)) --kv-unified"; else SLOTS="-c ${MAC_CTX:-65536}"; fi
  log "starting controller llama-server on $PRISM_PORT ($SLOTS)"
  nohup "$PRISM_DIR/build/bin/llama-server" -m "$GGUF_PATH" -ngl 99 -fa on $SLOTS --host 127.0.0.1 --port "$PRISM_PORT" \
    --alias "$MODEL_ALIAS" --jinja \
    --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64 \
    >"$LOG_DIR/server.log" 2>&1 &
  STARTED_PIDS+=("$!")
  echo "$!" >"$LOG_DIR/server.pid"   # the only process this script will ever stop
  wait_healthy "$PRISM_PORT" "controller server" || exit 3
fi

# --- reranker server (mac only: the gpu profile runs a torch cross-encoder inside the runner)
if [ "$KIND" = mac ]; then
  if healthy "$RERANKER_PORT"; then
    require_own_server "$RERANKER_PORT" "reranker server"
    log "reranker server already healthy on $RERANKER_PORT and owned by $(id -un): reusing it"
  else
    require_free_port "$RERANKER_PORT" "reranker server"
    log "starting reranker server on $RERANKER_PORT (scripts/reranker/serve_mac.sh)"
    LLAMA_SERVER="$PRISM_DIR/build/bin/llama-server" RERANKER_PORT="$RERANKER_PORT" nohup scripts/reranker/serve_mac.sh "${RERANKER_QUANT:-f16}" >"$LOG_DIR/reranker.log" 2>&1 &
    STARTED_PIDS+=("$!")
    echo "$!" >"$LOG_DIR/reranker.pid"
    wait_healthy "$RERANKER_PORT" "reranker server" || exit 3
  fi
fi

# --- the matrix
ARGS=(all --profile "$PROFILE" --run-dir "evaluation/runs/$RUN_ID" --execute --endpoint "http://127.0.0.1:$PRISM_PORT/v1")
[ -n "${MODEL_CONFIG:-}" ] && ARGS+=(--model-config "$MODEL_CONFIG")
[ -n "${MATRIX:-}" ] && ARGS+=(--matrix "$MATRIX")
[ "${SKIP_JUDGE:-0}" = "1" ] && ARGS+=(--skip-judge)
[ -n "${MAX_JUDGE_USD:-}" ] && ARGS+=(--max-judge-usd "$MAX_JUDGE_USD")
[ "$KIND" = gpu ] && ARGS+=(--server-note "gpu ${CUDA_VISIBLE_DEVICES}, $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1), llama.cpp prism, -np $NP -c $((NP * CTX_PER_SLOT))")
# shellcheck disable=SC2206
[ -n "${EXTRA:-}" ] && ARGS+=($EXTRA)
log "run_d2.py ${ARGS[*]}"
"$PYTHON" evaluation/run_d2.py "${ARGS[@]}" 2>&1 | tee -a "$LOG_DIR/run.log"
code=${PIPESTATUS[0]}
case "$code" in
  0) log "DONE: evaluation/runs/$RUN_ID (RUN_NOTES.md, tables/, analysis/summary.json)" ;;
  6) log "COLLECTED, JUDGE NOT RUN (no gateway credential here): copy evaluation/runs/$RUN_ID to a machine with the key and run: make judge RUN=evaluation/runs/$RUN_ID"; code=0 ;;
  2) log "STOPPED before completion (rows kept). Fix the cause and run THIS SAME COMMAND again to resume." ;;
  *) log "FAILED with exit code $code. Rows and the run directory are kept; see $LOG_DIR/run.log." ;;
esac
exit "$code"
