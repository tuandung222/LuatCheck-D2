# Diagnostic run: remote controller (openai/gpt-5.5) — not report evidence

Collected 23 October 2026 with `config/d2_gateway_diagnostic.yaml`: same frozen tasks, corpus, prompt, loop,
budgets and L1 checks as the D2 main run; only the controller model differs (remote API, reasoning effort low,
2048-token cap). 10 tasks x OFF/ON x seed 42 = 20 trials. Gateway-reported cost: USD 0.87 (not an invoice).

Purpose: separate task difficulty from small-model weakness. Status: `report_eligible: false`.

Caveats
- **Gateway response cache:** 20 of 48 response IDs recur across trials. When OFF and ON send byte-identical
  requests, the second trial reuses the first response (sub-second wall time). OFF and ON are therefore not
  independent samples, and latency of the second trial in a pair is not model latency.
- One seed only; the gateway route is not a pinned model revision.
- Correctness below is an AI assistant's comparison with the frozen reference answers, not a human label or
  the frozen DeepSeek judge protocol.

Observed (AI inspection): all 18 answerable trials answered with the gold article IDs and content consistent
with the reference answer; both foreign-scope trials refused appropriately; no execution errors.
In ON mode L1 forced 6 repairs on answers that were then accepted, mostly because a paraphrased `exact_quote`
was not verbatim in the source.
