# Historical red-team material

> **HISTORICAL — not current evidence (marked 23 October 2026).**

`redteam_results.json` and `adversarial_matrix_results.json` come from the retired pre-D2 pipeline. Their
"100% defense / 0% false-positive" figures were scored by refusal/keyword matching against the regex input
filter, with no established native-model provenance. They do not show resistance to paraphrased injections,
retrieved-content poisoning or real egress attempts, and are excluded from the D2 report (see
`evaluation/RESULTS_STATUS.md`). `make redteam` is disabled. Entry-point attack tests for the final report
are planned separately (D2 report, Section 6–7).
