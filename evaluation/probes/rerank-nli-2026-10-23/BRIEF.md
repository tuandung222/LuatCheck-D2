# Quick probe: Vietnamese reranker and NLI models on this Mac (23 Oct 2026)

You are running a short, real measurement. Work ONLY inside this directory:
  /Users/admin/Desktop/Recents/LuatCheck-D2/evaluation/probes/rerank-nli-2026-10-23/
Put the Python environment OUTSIDE the repo at ~/src/probe-venv (create with: uv venv ~/src/probe-venv --python 3.12).

## Hard rules (repository AGENTS.md applies)
- Do NOT modify anything outside the probe directory: no edits to src/, config/, report_d2/, tests/, data/, evaluation/*.py, README, AGENTS.md. Read them only.
- Do NOT read .env or any credential file. Do NOT commit, push or change git state.
- Do NOT stop, restart or call the running servers (llama-server on 127.0.0.1:8081, Ollama on 11434).
- Real models only. No mocks, no invented numbers. If a model fails to load or run, record the error and move on; do not fake its results.
- Labels of the probe pairs below are by construction from source text, NOT human labels; say so in the results.
- Keep the whole run under ~40 minutes. Free disk is limited (~55 GB): download at most the models listed.

## Inputs (read-only)
- Corpus: /Users/admin/Desktop/Recents/LuatCheck-D2/data/corpus/labor_code_2019_official.json (220 articles: article_id like "Dieu_25", title, content).
- Tasks: /Users/admin/Desktop/Recents/LuatCheck-D2/evaluation/benchmarks/bll2019_v1/tasks.json (10 tasks; fields task_id, question, expected_behavior, expected_answer, ground_truth_article_ids, reference_evidence[{article_id, exact_quote}]).
- Current first-stage retriever (import it, do not change it): run with PYTHONPATH=/Users/admin/Desktop/Recents/LuatCheck-D2 and use
  `from src.retrieval.hybrid_domain import HybridDomainRetriever; r = HybridDomainRetriever(corpus_path=<corpus>, retrieval_mode="tfidf"); r.search(query, top_k=20)`
  (returns dicts with article_id and content). It needs rank-bm25 and scikit-learn in the venv.

## Models to test
1. AITeamVN/Vietnamese_Reranker (cross-encoder reranker, transformers AutoModelForSequenceClassification, max_length 2304).
2. Qwen/Qwen3-Reranker-0.6B (reranker; follow its model card's yes/no scoring recipe with transformers).
3. MoritzLaurer/mDeBERTa-v3-base-mnli-xnli (NLI; labels 0=entailment, 1=neutral, 2=contradiction; fp32 only; 512 tokens).
4. Optional, only if time remains: OmniJev/OneJev1.6-0.8B (System One decision model). Read its model card for the official API; if it cannot run on MPS/CPU within ~10 minutes of effort, record why and skip.
Use device "mps" when it works, else "cpu"; record which.

## Experiment A: reranking (9 answerable tasks; skip BLL19-10-FOREIGN_SCOPE)
For each task: candidates = HybridDomainRetriever top-20 for the task question. Record the rank of each gold article (ground_truth_article_ids) before reranking (first-stage order) and after reranking with each reranker (score each question/article-content pair). Report per model: Recall@1, Recall@3, Recall@5 (fraction of gold IDs in top-k, averaged over tasks), MRR (first gold), plus per-task gold ranks. Note how many gold articles are absent from the top-20 (reranking cannot recover them).

## Experiment B: NLI probe pairs (mDeBERTa; also OneJev if it runs)
Build pairs from the tasks' reference_evidence exact_quote (premise = the quoted clause):
- entailment-by-construction: hypothesis = the task's expected_answer (or a faithful restatement) for answerable tasks;
- contradiction-by-construction: change the key quantity or polarity of the same statement (e.g. "Không quá 60 ngày" -> "Không quá 90 ngày"; "không được" -> "được");
- neutral-by-construction: hypothesis = the expected_answer of a different task on an unrelated topic.
Also include two real model outputs as extra cases (premise = full content of the cited article):
- Dieu_17 content vs "Người sử dụng lao động được phép yêu cầu người lao động nộp tiền đặt cọc để bảo đảm thực hiện hợp đồng lao động." (expected: contradiction)
- Dieu_107 content vs "Theo luật bang California, số giờ làm thêm tối đa là 200 giờ một năm." (expected: neutral)
Report the predicted label and the three probabilities per pair, accuracy per constructed class, and how many premises exceeded 512 tokens (truncation).

## Also measure
For each model: load time, median and p95 latency per pair (after one warm-up), peak process memory (use psutil RSS and, on MPS, torch.mps.current_allocated_memory / driver_allocated_memory if available), device used.

## Deliverables in the probe directory
- probe.py (the code you ran; re-runnable)
- results.json (all raw numbers, per-task ranks, per-pair predictions, timings, errors)
- RESULTS.md: a short summary table, every failure and its error, and an explicit caveat block: tiny sample (9 queries, constructed NLI pairs), not a benchmark, not human-labelled, not report evidence.
Finish by printing RESULTS.md.
