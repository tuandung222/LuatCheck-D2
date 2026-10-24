# D2 supervisor handoff: what was done and why

Written 2026-10-25 01:50 +07 by the supervising agent (Claude Opus) at the end of its session, for review by another agent.
Supersedes `docs/HANDOFF_2026-10-24.md` where they differ; that file keeps the detailed history of 23–24 Oct.

- Repository: https://github.com/tuandung222/LuatCheck-D2 (public).
- Branch `main`.
- Source revision cited on the report cover and slide footer: `d74144099016bc940ce8d033c3ce6376c491603d`.
- Last commit at the time of writing: `fe48219` (hash stamp), plus the commit that adds this note.

## 1. Roles and ground rules

- **Who did what:** the owner (Võ Phạm Tuấn Dũng) set the goals. This agent supervised, reviewed and verified. Implementation was mostly delegated to Sonnet sub-agents, then checked here, often by recomputing numbers independently.
- **Rules followed throughout:**
  - Commits are authored as `tuandung222 <tuandung12092002@gmail.com>` only, with no Claude trailer. This is the owner's explicit rule and overrides any tool default.
  - `AGENTS.md` integrity rules apply: real inference only, no mocks or monkeypatching, no fabricated numbers, human labels or member contributions. Missing evidence stays a visible red placeholder.
  - `.env` is never read and keys are never printed. The judge key comes from `local_environment`.
  - Agents may not run `rm` or delete files. Moves use `git mv`. Temporary files go to the session scratchpad.
  - Server 82 is shared: only `dungvpt` processes, free GPUs only (2 and 3 were allowed), loopback ports we own, data on NFS.
  - The owner needs the Mac's RAM, so every model server started for a task is stopped afterwards.
  - Locked benchmark files and locked profile YAMLs are never edited.
- **Out of scope here:** the team-owned items in `docs/TEAM_INPUTS_D2.md` (human audit labels and κ, contribution evidence, self-checks, presenters, plan owners, the submission email). The owner handles these with a different agent. Do not fill them in.

## 2. Final state of the deliverables

| What | Where | State |
|---|---|---|
| D2 report (submitted) | `deliverables/d2/report/main_d2.pdf` (source `main_d2.tex`) | 15 pages including cover, TOC, references and appendix (content ≤ 10). `make report-check` OK, 33 tables. Red placeholders remain only for team items (audit κ, contributions, self-checks, plan owners). |
| D2 slides (submitted) | `deliverables/d2/slides/main.pdf` | 16 pages (12 + 4 backup), HCMUT Beamer template. Footer commit `d74144099016`. Speaker notes in `SPEAKER_NOTES.md`. |
| Demo | `deliverables/d2/demo/` | `DEMO_SCRIPT.md`; GIFs; backup video `gifs/demo_backup_4b.mp4`; recorder `record_demo.py` with scenarios. |
| Index | `deliverables/README.md` | Which PDFs are submitted and how to build them. |
| D1 / D3 | `deliverables/d1/{report,slides}`, `deliverables/d3/report` | Moved only, contents unchanged; D3 is historical. |
| Repo docs | `README.md` (GIFs + architecture), `docs/REPRODUCE_D2.md`, `docs/BENCHMARKS_AND_METRICS.md`, `docs/L1_VERIFIER.md`, `docs/D2_WORK_ITEMS.md`, `docs/HUMAN_AUDIT_GUIDE.md`, `docs/TEAM_INPUTS_D2.md` | Current. |

**Build commands:**
- `make report_d2` builds the report and `make -B slides_d2` builds the slides. The Make target names kept their old spelling on purpose.
- `make report-check` checks provenance and `make runs` regenerates the registry.

## 3. Decisions and the reasons for them

### 3.1 One locked harness, two controllers
- **Decision:** a single harness version (`HARNESS_VERSION 1.2.0`) for benchmark and demo. The chosen system is the revised system "r2" with the Ternary Bonsai 4B controller, L1 verifier and reranker. The demo profiles are `config/profiles/demo-hcmut.yaml` and `demo-labour.yaml`; the `-2b` profiles are the same system with the 2B controller.
- **Why:** the owner objected to multiple versions in flight ("chốt duy nhất một version"). 4B more than doubles strict success over 2B, and 2B is kept because it is about twice as fast.
- **Opt-in switches:** every r2 change is a config switch whose default reproduces the original frozen system v3, so the v3 runs replay unchanged. The switch list is in `docs/plans/D2_REVISION_L1_BONSAI4B.md`.
- **Post-hoc disclosure:** r2 was designed after seeing the v3 results on the same tasks. The report and README say so plainly.

### 3.2 Experiment tracking
- **Rule:** every reported number comes from a recorded run directory under `evaluation/runs/`. Each run records harness version, commit, a source snapshot and a collection fingerprint.
- **Pins:** each run is pinned to the commit that produced it in `evaluation/runs/registry_overrides.yaml`, and every pin was verified against git sources.

  | Runs | Pinned commit |
  |---|---|
  | v3 | 957579b |
  | r2 GPU, 2B and 4B | cdb6b24 |
  | Mac latency, 4B | 8cdd28d |
  | Mac latency, 2B | 6e6e48a |

- **Why pin:** later commits (docs, UI, the folder move) must not mark results as stale or silently change them, which the owner stressed ("chỉ cần… không làm thay đổi số liệu").
- **Fingerprint scope:** UI-only directories (`src/api`, `src/services`, `src/ui`) are excluded from the collection fingerprint, so frontend work does not stale benchmark runs.
- **Report gate:** `make report-check` fails if a report table is not from a `current` or `pinned` main run.
- **Cited revision:** the report cites a "reported revision". It is the final source state the lecturer should read; numbers are tied to the pinned run commits, not to this hash.

### 3.3 Benchmarks and metrics
- **Benchmarks:** two frozen, hash-locked 50-task benchmarks, `hcmut_v1` and `labour_vi_v1`. The owner reviewed all 100 tasks on 23 Oct around 23:00; the record is in `docs/reviews/benchmark_human_review_2026-10-23.md`. It is kept outside the benchmark directories so the fingerprints do not change.
- **Headline metric:** strict success from an LLM judge (DeepSeek V4 Flash via the gateway). It is a lower bound: execution errors and unjudged packets count as failures.
- **Refusal fix:** correct refusals were first counted as failures. This was fixed through `evaluation/judge_rules.py`.
- **Statistics:** paired bootstrap CIs over 3 seeds.
- **Baselines:** closed-book (no retrieval) and oracle (gold section given), one seed each, as the owner asked.
- **Judge cost:** about USD 5.5 for the six main runs (gateway-reported, not an invoice), plus 368 attempts with no reported cost. An older figure of USD 1.6 was stale and has been corrected.

### 3.4 Results (all recomputed independently)

**Strict success, full system (verifier + reranker), %:**

| Benchmark | v3-2B | r2-2B | r2-4B |
|---|---|---|---|
| HCMUT | 14.0 | 28.7 | **60.7** |
| Labour | 18.7 | 28.0 | **56.7** |

All CIs of the system effect and the model effect exclude 0.

**Findings to keep honest:**
- **Verifier and reranker do not raise strict success.** The variant with neither is highest (4B: 70.0 / 62.0).
- **L1 reduces answers the judge marks as contradicted** (e.g. 2B labour 38 → 19) and raises precision for 2B. The mechanism and numbers are in `docs/L1_VERIFIER.md`.
- **The reranker only helped v3.** It raised Recall@5 on labour by 15.6 points. In r2, retrieval is saturated (Recall@5 ≈ 0.99).
- **Baselines for 4B:** oracle 82.2 / 75.6; closed-book 2.0 / 24.0.

**Mac latency (Apple M4, chosen system), median / p95 per question:**

| Controller | HCMUT | Labour | Throughput |
|---|---|---|---|
| 4B | 33.0 / 86 s | 29.8 / 72 s | ≈ 43 tok/s |
| 2B | 13.3 / 30 s | 14.6 / 28 s | ≈ 92 tok/s |

### 3.5 Code fixes made during the session (each with a regression test or a rerun)
- **Shared reranker race** ("Already borrowed" with 16 workers): fixed with an `RLock` on `BaseReranker`, held during scoring, in `src/retrieval/rerankers.py` and `src/tools/domain_tools.py`.
- **L1 crash** on quantities spanning a newline: `re.S` in `_quantity_key` in `src/verifier/lexical_grounding.py`. The runs made before the fix are superseded.
- **Web runtime ignored `profile_variant`:** fixed in `src/api/runtime.py`.
- **Preflight context-size mismatch on GPU:** `--kv-unified` added to the GPU server command.
- **L1 v2 default:** an agent made v2 the default, which would have silently changed v3. The default was reset to v1.
- **Tooling bugs:**
  - The registry ignored 4B pins.
  - The table renderer printed a literal TAB in its banner.
  - The answer-rate caption used the wrong denominator.
  - Latency-only tables were rejected by the provenance check.

### 3.6 Demo recordings (25 Oct, real runs, nothing edited)
- **Where each controller is used:** the 4B recordings feed the slides and the backup video (the live-demo configuration). The 2B recordings feed the README, because 2B is faster and the GIFs stay short; this was the owner's choice. Captions state which controller was used.
- **4B files:**
  - `11_hcmut_answer_4b.gif`: answer, 23.6 s.
  - `12_labour_answer_4b.gif`: answer, 21.0 s.
  - `13_verifier_repair_4b.gif`: L1 rejects the first draft, then one repair gives a passing answer, 49.2 s. Only 1 of 6 tries ended in an answer after a repair; this is not a repair rate.
  - `14_hcmut_refuse_4b.gif`: refusal.
  - `15_guardrail_4b.gif`: guardrail block.
  - `demo_backup_4b.mp4`: 2 min 37 s.
- **2B files:**
  - `21_hcmut_answer_2b.gif` (also the README hero) and `22_labour_answer_2b.gif`: the best of 3 runs each.
  - `23_verifier_repair_2b.gif`: two repairs, then an L1-failure refusal (a real failure case, captioned as one).
- **Demo reliability on the live queries:** 4B answered 14/14 runs. 2B had 4/16 runs that clarified or refused instead of answering. This is a small sample on two easy questions, not accuracy. See `deliverables/d2/demo/DEMO_SCRIPT.md` §1, §4 and §8.
- **Recommendation:** present live on 4B (about 20–26 s for the two demo answers).

### 3.7 Folder restructure (commits `6e45c6f`, `d741440`)
- **What moved:** `report_d1`, `report_d2`, `slides_d2`, `docs/presentation` and `report_d3` went into `deliverables/d1|d2|d3/{report,slides,demo}`. The first commit is a pure `git mv`: 92 renames at 100% similarity, nothing deleted. The second commit fixes references.
- **Why:** the owner asked for one place for course deliverables.
- **Left untouched on purpose:** everything under `evaluation/runs/**` (historical artifacts keep their old paths), dated review notes, and the `% generator:` headers of already generated tables (they record the command actually run).
- **Verification:**
  - `make runs` is identical before and after (43 runs; pinned 8, current 1, stale 6, historical 20, incomplete 2, remote 5, n/a 1). `registry.jsonl` is byte-identical.
  - `make report-check` is OK.
  - The report and slide PDF text is identical page by page.
  - Tests with the controller and reranker servers up: 427 passed, 2 skipped, 1 failed. The failure is `test_real_native_end_to_end`, which needs Ollama on :11434. Without servers, only connection errors appear.
  - All servers were stopped afterwards.

### 3.8 Report and slides style
- **Audience:** the lecturer, so lecturer-facing wording ("initial system / current system", "no verifier / verifier / verifier + reranker"), with no internal labels (v3, r2, run ids, paths) and no source paths.
- **Format:** few tables and visual figures (architecture TikZ, trace, UI screenshot, bar chart). Mac latency is given in prose.
- **AI-use disclosure:** written in the group's words. The group used several AI models; ideas, supervision, code review and task assignment were the group's own.

## 4. What a reviewer should check first
1. Run `make runs` and `make report-check` on a clean checkout. Expect the counts in §3.7 and "OK: 33 result tables".
2. Compare report numbers against `evaluation/comparisons/v3-2B_vs_r2-2B_vs_r2-4B/comparison.md` and the run `analysis/summary.json` files.
3. Open README and confirm the 3 GIFs render from `deliverables/d2/demo/gifs/`.
4. Confirm `git log --format='%an' | sort -u` shows only team members (Võ Phạm Tuấn Dũng and tuandung222 are the same person), with no Claude author.

## 5. Known gaps and risks (not fixed in this session)
- **Judge versus humans:** the team's human audit (60 packets) is still missing, so all correctness numbers are LLM estimates until κ is known. Packets are in `evaluation/runs/d2-gpu-r2-4b-{hcmut,labour}-v1/analysis/human-audit/`.
- **Benchmarks are easy for retrieval** (Recall@5 ≈ 0.99 in r2). A harder benchmark is proposed in `docs/plans/BENCHMARK_V2_PROPOSAL.md` but not started.
- **Not evaluated:** L2 NLI and dense embeddings exist in code. Ablations are planned for the final report.
- **Stale planning figure:** `docs/HANDOFF_2026-10-24.md` line ~163 says "≈USD 0.7 per run". `REPRODUCE_D2.md` already flags it.
- **Broken links:** two links in `deliverables/d2/report/D2_GAP_REVIEW.md` point to files that were already missing before the move.
- **Ignored audit logs:** the demo audit logs `data/demo_*audit_log*.jsonl` are now gitignored.
- **4B latency tail:** 4B can take 70–90 s on about 1 in 20 questions. The slides and demo script say so; keep 2B as a faster fallback window.
- **Submitted hash:** the hash the lecturer receives with the submission should be the final `main` commit at submission time. The report cites the source revision `d74144099016`; later commits only add docs and must not change any number. Check with `make report-check`.
