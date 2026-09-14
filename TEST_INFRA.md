# TEST_INFRA.md — Dual-Track Testing Infrastructure Specification

## 1. Executive Summary & Architecture Overview
The LuatCheck testing infrastructure implements an enterprise-grade **Dual-Track Testing Architecture** designed for safety-critical, evidence-grounded legal AI systems.
- **Track A (Deterministic Unit & Boundary Verification)**: Exhaustively tests single-component integrity, statutory corpus adherence, regex boundary invariants, and edge cases.
- **Track B (Systemic Integration & Workload Stress)**: Tests cross-module contracts, FSM state preservation under adversarial mutation, air-gap offline operational envelopes, and real-world Vietnamese legal dispute workloads.

The test harness is executed natively via `pytest` with 459 passing automated tests across 17 test suites, integrated into the repository build system via `Makefile` (`make test`, `make eval`, `make redteam`).

```
+--------------------------------------------------------------------------------------------------+
|                                    LUATCHECK TEST HARNESS (pytest)                              |
+--------------------------------------------------------------------------------------------------+
|  Tier 1: Feature Coverage (>=5 per feature across 20 features = 100+ tests)                      |
|  - Agent Loop, MCP Tools, L1/L2 Verifier, Memory & PII, Guardrails, UI, Audit Logger             |
+--------------------------------------------------------------------------------------------------+
|  Tier 2: Boundary & Corner Cases (>=5 per feature across 20 features = 100+ tests)               |
|  - Zero-width unicode, regex padding, budget exhaustion, cache corruption, token thresholds      |
+--------------------------------------------------------------------------------------------------+
|  Tier 3: Cross-Feature Combinations (Pairwise Inter-Module Interactions)                         |
|  - Guardrails + Cache Hit, Budget Limits + Verifier Feedback, HITL Egress + Idempotency + Modal  |
+--------------------------------------------------------------------------------------------------+
|  Tier 4: Real-World Legal Workloads (VLQA + End-to-End Enterprise Scenarios)                     |
|  - Maternity Protection, Illegal Firing, Probation Wage Violations, Severance Restructuring    |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Test Directory & Suite Mapping
The test suite resides in `tests/` and maps directly to the system components:

| Test File | Primary Scope | Test Count | Key Modules Exercised |
|:---|:---|:---:|:---|
| `tests/test_adversarial_guardrails.py` | Boundary evasion, zero-width, fullwidth brackets | 38 | `src/security/guardrails.py` |
| `tests/test_adversarial_memory.py` | Adversarial PII mutations, cache re-verification | 48 | `src/memory/sqlite_store.py`, `src/agent/loop.py` |
| `tests/test_agent_loop.py` | ReAct FSM transitions, budget caps, ablation | 9 | `src/agent/loop.py`, `src/agent/state.py` |
| `tests/test_challenger_m1_4_security.py` | Evasion stress & false positive validation | 125 | `src/security/guardrails.py` |
| `tests/test_challenger_m1_iter2.py` | Multi-iteration regression guard | 57 | `src/security/guardrails.py` |
| `tests/test_challenger_m3.py` | M3 Error diagnostics, boundary values & statutory compliance | 14 | `evaluation/error_analyzer.py`, `src/verifier/` |
| `tests/test_challenger_m4.py` | M4 Multi-seed metric consistency & poisoned shard defenses | 18 | `evaluation/error_analyzer.py`, `src/verifier/` |
| `tests/test_challenger_m5.py` | M5 LaTeX report compilation & empirical table fidelity | 13 | `report_d2/`, `evaluation/`, `redteam/` |
| `tests/test_error_analyzer.py` | 6-mode failure taxonomy & diagnostic statistics | 9 | `evaluation/error_analyzer.py` |
| `tests/test_l2_verifier.py` | L2 Semantic Entailment (NLI) & TF-IDF/SLM comparator | 34 | `src/verifier/l2_semantic.py` |
| `tests/test_mcp_tools.py` | MCP tool definitions & permission gating | 4 | `src/tools/legal_tools.py`, `src/tools/permissions.py` |
| `tests/test_memory.py` | Dual-tier memory & PDPL 2025 PII sanitization | 9 | `src/memory/sqlite_store.py`, `src/memory/ledger.py` |
| `tests/test_offline.py` | Air-gap offline verification (zero network calls) | 1 | `src/agent/loop.py`, all core modules |
| `tests/test_security.py` | Guardrail regex patterns, sanitization, utility | 43 | `src/security/guardrails.py`, `evaluation/metrics.py` |
| `tests/test_ui.py` | Streamlit UI columns, traces, HITL modal | 12 | `src/ui/app.py` |
| `tests/test_ui_stress.py` | UI sentence grounding, SHA256 idempotency & rendering | 21 | `src/ui/app.py`, `src/tools/legal_tools.py` |
| `tests/test_verifier.py` | L1 deterministic verifier & baseline L2 verification | 4 | `src/verifier/l1_deterministic.py`, `src/verifier/l2_semantic.py` |
| **Total Automated Tests** | **Comprehensive Full System Dual-Track Harness** | **459** | **100% Passing (`pytest tests/ -v`)** |

---

## 3. Four-Tier Testing Hierarchy

### Tier 1: Feature Coverage (>=5 test cases per feature across 20 features)
Covers all 20 features declared in `PROJECT.md`:
1. **BudgetedReActLoop**: FSM transitions, initialization, tool execution, terminal state, offline fallback.
2. **TargetedRepair**: Verifier feedback formatting, repair counter decrement, repair prompt template, repair history logging, recovery to answer.
3. **search_law [RO]**: Single-keyword search, multi-word legal query, top-k limiting, BM25 scoring, empty corpus handling.
4. **get_article [RO]**: Valid article ID retrieval, non-existent article error handling, content completeness, title extraction, casing invariance.
5. **save_case [RW]**: Session case saving, verified case persistence, parameter validation, schema compliance, rollback on DB error.
6. **send_summary [HITL]**: Blocked without confirmation, success with confirmation, audit logging, recipient validation, notification payload format.
7. **L1_ExistenceCheck**: Valid article ID check, non-existent article detection (>220 articles), decree code validation, circular code validation, empty citation check.
8. **L1_ProvenanceCheck**: Retrieved in active session passes, unretrieved citation flagged as hallucination, cache provenance synchronization, multiple citations provenance, empty retrieved list handling.
9. **L1_SpanSupportCheck**: Overlap >= 25% passes, overlap < 25% fails, stopword filtering, punctuation removal, multi-sentence span verification.
10. **CaseLedger**: Session creation, query addition, fact extraction & deduplication, tool call recording, cache hit recording.
11. **SQLiteEpisodicStore**: Database schema creation, verified answer write policy, unverified answer rejection, similar case retrieval (similarity >= 0.85), index version filtering (`v2026.1`).
12. **SecurityGuardrails**: Direct injection detection, roleplay evasion detection, illegal legal advice blocking, indirect document injection blocking, passive wrapper formatting.
13. **AuditLogger**: JSONL event formatting, epoch/timestamp logging, session ID correlation, latency tracking, event type diversity (`security_refusal`, `cache_hit`, `session_completed`).
14. **Reproducibility & Config**: `pytest.ini` pythonpath configuration, `requirements.txt` pinned versions, `Makefile` one-command targets, `config.yaml` loading, corpus JSON schema validity.
15. **Agent Loop Unit Tests**: Offline fallback execution, rule-based reasoning, LLM format json parsing, state transition assertion, multi-turn loop progression.
16. **Streamlit Demo UI**: 3-column layout rendering, preset scenario selection, live trace display, grounding card rendering, audit log inspection stream.
17. **Multi-Seed Evaluation**: Multi-seed CLI invocation, seed 42/123/2026 reproducibility, ablation ON vs OFF, metric calculation (ASR, unsupported rate, precision/recall), output table generation.
18. **Red Teaming Suite**: Direct prompt injection suite, indirect contract injection suite, poisoned retrieval shard suite, ASR calculation, defense rate calculation.
19. **LaTeX Progress Report**: Template compilation, bibliography compilation (`bibtex`), zero broken citations, page count verification, math formula rendering.
20. **Final E2E Acceptance & Audit**: Complete test pass, no git-uncommitted changes, PDPL compliance validation, deterministic refusal assertion, air-gap offline assertion.

### Tier 2: Boundary & Corner Cases (>=5 test cases per feature)
- **Extreme string pressure**: 1000+ character padding, repetitive strings, empty strings, pure whitespace.
- **Adversarial typography**: Zero-width spaces (`\u200b`, `\u200c`, `\u200d`, `\ufeff`), null bytes (`\x00`), fullwidth unicode brackets (`［`, `］`).
- **Delimiter smuggling**: `[/UNTRUSTED_USER_QUERY]`, `[SYSTEM_NOTE]`, `<!-- HTML comments -->`, Markdown link egress payloads.
- **Budget boundary invariants**: Execution at tool call count = 4, 5 (limit), and 6 (hard block); repair round = 1, 2 (limit), and 3 (deterministic refusal).
- **Cache boundary invariants**: Index version mismatch (`v2025.1` vs `v2026.1`), corrupt article IDs in DB (`Dieu_9999_Fake`), contradictory semantic claims.

### Tier 3: Cross-Feature Combinations (Pairwise Inter-Module Interactions)
- **Guardrails + Cache System**: Ensures that an injection query hitting the agent is stopped at the guardrail before checking or poisoning the episodic cache.
- **ReAct Budget + L1 Evidence Verifier**: When verification fails repeatedly, ensures the loop consumes targeted repair budget and transitions to refusal without spinning infinitely.
- **HITL Egress Gate + SHA256 Idempotency + UI Modal**: Guarantees that even if an attacker attempts an indirect egress injection through a contract, the egress requires explicit modal confirmation AND duplicate keys are suppressed.
- **Dual-Tier Memory + PDPL Sanitization**: Verifies that when a query containing phone/CCCD/email is verified and persisted, the stored record is scrubbed, and subsequent semantic retrieval returns sanitized content.
- **L1 Deterministic + L2 Semantic Entailment**: Verifies that a generated claim passing L1 span overlap is still rejected if L2 detects contradiction or unsubstantiated extrapolation.

### Tier 4: Real-World Vietnamese Legal Workloads
- **Scenario 1: Female employee maternity dismissal dispute** (Articles 37 & 122).
- **Scenario 2: Probation period wage & duration dispute for university graduates** (Articles 25 & 26).
- **Scenario 3: Unilateral contract termination without notice rights** (Article 35).
- **Scenario 4: Unauthorized salary deductions and property damage dispute** (Article 129).
- **Scenario 5: Severance allowance calculation under corporate restructuring** (Article 46).

---

## 4. Test Execution & Automation Guide
- **Execute all tests**: `make test` or `PYTHONPATH=. pytest tests/ -v`
- **Execute security tests only**: `pytest tests/test_security.py tests/test_adversarial_guardrails.py -v`
- **Execute memory & cache tests**: `pytest tests/test_memory.py tests/test_adversarial_memory.py -v`
- **Execute offline integrity test**: `pytest tests/test_offline.py -v`
- **Execute UI & stress tests**: `pytest tests/test_ui.py tests/test_ui_stress.py -v`
