# LuatCheck integrity rules

- Application, demo and experiment entry points must use real configured inference. Never replace an unavailable or malformed model response with a rule-based/mock answer.
- A backend failure is an execution error, not a successful answer, a safety refusal, or a zero-cost measurement.
- No mocked tests, models, HTTP responses, injected stand-in components, monkeypatching, or canned model actions are permitted. Test real implementations with source-backed data and native inference. Temporary storage is allowed; component substitution is not.
- Label lexical scores as lexical proxies. Answer-correctness claims require separate reviewed evidence. Never manufacture scores, token counts, hardware use, human labels, provenance, or member contributions.
- Keep unverified historical results out of current report tables. Preserve their historical status.
- Missing empirical results in the D2 draft must remain visible red placeholders until supported by replayable run artifacts.
- The latest user request authorizes real benchmarking on this Mac and report completion. Preserve failed runs, freeze the selected benchmark before main collection, and never fill missing evidence with fabricated scores or human labels.

# Direction: domain-general assistant

The long-term goal is a grounded assistant for any document domain, not only law. The current release covers one domain (the original 2019 Vietnamese Labour Code); keep that scope in claims until another domain is actually evaluated.

- New core code must stay domain-agnostic: generic document IDs, tool names and contracts (e.g. `src/tools/domain_tools.py`, `src/contracts/universal_document.py`), with domain specifics in data and configuration.
- Keep domain-specific parts behind explicit, swappable per-domain modules or config: system prompt, tool names/descriptions (`search_law`, `get_article`), ID conventions (`Dieu_<n>`), guardrail patterns, L1 quantity units, and benchmark tasks/rubrics. Do not add new legal-only assumptions to shared code.
- A new domain needs its own source-backed corpus with provenance, its own reviewed tasks and evaluation run before any claim about it. Do not reuse labour-law results as evidence for other domains.
