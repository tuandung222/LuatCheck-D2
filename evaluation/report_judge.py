"""Insert actual LLM-judge estimates into the D2 draft without human claims."""
import argparse
import json
from pathlib import Path


def render(summary_path):
    data = json.loads(Path(summary_path).read_text())
    rows = []
    modes = [data["modes"][m] for m in ("off", "l1_on")]
    def line(label, cells):
        rows.append(label + " & " + " & ".join(cells) + r"\\")
    line("Valid / judgeable judgments", [f'{m["valid_judgments"]} / {m["judgeable_judgments"]}' for m in modes])
    line("Strict task successes (LLM estimate)", [f'{m["success_count_estimate"]} / {m["known_outcome_denominator"]} known' for m in modes])
    line("Unknown task outcomes", [str(m["unknown_task_outcomes"]) for m in modes])
    bounds = []
    for m in modes:
        low, high = m["success_rate_lower_bound_all_trials"], m["success_rate_upper_bound_all_trials"]
        bounds.append(f"{100*low:.1f}\\%" if low == high else f"{100*low:.1f}--{100*high:.1f}\\%")
    line("Strict success over all 30 trials", bounds)
    line("Supported / total factual claims", [f'{m["supported_claims"]} / {m["factual_claims"]}' for m in modes])
    line("Claim faithfulness (LLM estimate)", [f'{100*m["claim_faithfulness_estimate"]:.1f}\\%' if m["claim_faithfulness_estimate"] is not None else "N/A" for m in modes])
    line("Unsupported claims (LLM estimate)", [f'{100*m["unsupported_claim_rate_estimate"]:.1f}\\%' if m["unsupported_claim_rate_estimate"] is not None else "N/A" for m in modes])
    line("Human agreement / Cohen's kappa", [r"\pending{human labels}" for _ in modes])
    text = (r"\begin{table}[H]\centering\footnotesize" "\n"
            r"\begin{tabularx}{\textwidth}{@{}L{6.0cm}XX@{}}\toprule Uncalibrated semantic estimate & OFF & L1 ON\\\midrule" "\n"
            + "\n".join(rows) + "\n" + r"\bottomrule\end{tabularx}" "\n"
            r"\caption{Independent DeepSeek Flash gateway judgments. These are LLM estimates, not human-validated accuracy. Bounds retain invalid/unjudgeable outputs as unknown, not confidence intervals; known execution errors remain failures. Claim rates use factual claims in valid judgeable outputs, including claims in refusals/clarifications. Zero-claim outputs do not create perfect faithfulness.}" "\n"
            r"\end{table}" "\n")
    usage = data["api_usage"]
    prompt = f'{usage["prompt_tokens"]:,}' if usage["prompt_tokens"] is not None else r"\pending{unknown}"
    completion = f'{usage["reported_completion_tokens"]:,}' if usage["reported_completion_tokens"] is not None else r"\pending{unknown}"
    cost = f'USD {usage["gateway_reported_cost_usd"]:.6f}' if usage["gateway_reported_cost_usd"] is not None else r"\pending{unknown}"
    if usage["usage_complete"]:
        metering = f'The gateway reported {prompt} prompt tokens and {completion} completion tokens. '
    else:
        metering = (f'Usage is available for {usage["metered_attempts"]} attempts: '
                    f'{usage["observed_prompt_tokens_subtotal"]:,} reported prompt and '
                    f'{usage["observed_completion_tokens_subtotal"]:,} reported completion tokens. '
                    f'{usage["missing_usage_attempts"]} attempts have unknown usage; no complete total is claimed. ')
    if usage["gateway_reported_cost_usd"] is not None:
        billing = f'The gateway reported {cost}. '
    else:
        billing = (f'The response-body usage.cost subtotal is USD {usage["body_usage_cost_subtotal_usd"]:.6f}; '
                   f'cost is missing for {usage["missing_cost_attempts"]} attempts. ')
    if usage.get("body_header_cost_conflicts"):
        billing += (f'The separate response-header subtotal is USD {usage["header_cost_subtotal_usd"]:.6f} '
                    f'over {usage["header_cost_attempts"]} attempts; the two reported cost fields disagree in '
                    f'{len(usage["body_header_cost_conflicts"])} records, so neither is certified as the actual charge. ')
    text += (f'The main and recovery judging batches made {usage["attempts_including_failed"]} API attempts '
             '(including retained failed attempts). ' + metering + billing
             + 'These are gateway-reported costs, not an independently verified invoice. Remote judge hardware and active GPU time are unknown. '
             f'A reproducible stratified human-audit package contains {data["human_audit_sample"]["count"]} validly judged '
             f'outputs; {data.get("targeted_unresolved_review",{}).get("count",0)} unresolved outputs are provided for a separate targeted review. '
             r'The human label sheet is blank. \pending{Complete the human audit and report actual agreement and Cohen\textquotesingle s kappa.}' + "\n")
    text += "Two earlier judge pilot calls are retained separately and are not merged into these main metrics or cost subtotals.\n"
    if usage.get("usage_consistency_anomalies"):
        text += (f'The gateway returned {len(usage["usage_consistency_anomalies"])} usage records whose reasoning-token detail exceeds '
                 'the reported completion-token field. Original values are retained without correction; these are provider-reported '
                 'counters, not independently certified physical token counts.\n')
    if data.get("parser_revalidation_overrides"):
        text += ('A provenance-parser correction permits a known article ID with a null quotation for '
                 'not-established claims, as allowed by the frozen rubric. Complete raw judgments were revalidated without '
                 'editing any model score, label or quotation; original validation failures remain preserved.\n')
    if data.get("recovery_history"):
        text += ('Recovery was added after observing API/validation failures and was not preregistered. '
                 'Every phase covers all and only still-invalid judgments; each task stops at its first valid judgment, '
                 'regardless of semantic score. Model, semantic prompt and task inputs are unchanged. ')
        for phase in data['recovery_history']:
            cfg = phase['config']
            text += (f"A streamed phase retried {phase['trials']} outputs with up to {cfg['max_attempts']} "
                     f"attempts per output, a {cfg['max_tokens']:,}-token cap and concurrency {cfg['concurrency']}; "
                     f"{phase['valid']} judgments passed validation. ")
        text += ('All attempts, including failures and available usage/cost, are retained. '
                 'Previously accepted judgments were never resampled.\n')
    elif data.get("recovery"):
        raise ValueError('Recovery history required for accurate reporting')
    # Avoid adding a package solely for a quote character.
    text = text.replace(r"Cohen\textquotesingle s", "Cohen's")
    return text


def update(summary_path):
    report = Path("deliverables/d2/report/main_d2.tex")
    text = report.read_text()
    Path("deliverables/d2/report/semantic_results.tex").write_text(render(summary_path))
    if r"\input{semantic_results.tex}" not in text:
        text = text.replace(r"\input{native_results.tex}", r"\input{native_results.tex}" + "\n" + r"\input{semantic_results.tex}")
    text = text.replace(
        r"\pending{Record the actual independent judge, settings, responses, semantic metrics and reliability on a human-labelled sample.}",
        r"The group selected DeepSeek V4.1 Flash. The Qualgo gateway exposes \code{deepseek/deepseek-v4-flash}, identifies the provider as DeepSeek, and returns that same model ID. Official DeepSeek documentation maps the legacy upstream alias to V4.1-Flash-1017~\citep{deepseek2026api}; this mutable gateway route is not an independently attested or pinned model revision. The judge uses thinking enabled, high reasoning effort, an 8,192-token completion cap, JSON output and at most two retained attempts per output; no seed or effective sampling temperature is claimed. Strict success requires appropriate behaviour, correctness 2/2, completeness 2/2 and every factual claim supported. The gateway receives curated benchmark questions, answers and statutory sources separately from local controller inference. Full prompts, raw responses, model IDs and usage are retained. \pending{Human reliability validation remains incomplete.}")
    text = text.replace("Independent semantic scoring remains pending; this qualitative case does not supply a benchmark accuracy estimate.",
                        "Independent LLM-judge estimates are reported separately; this qualitative inspection is not a human correctness label.")
    text = text.replace("Semantic scoring remains pending; no public VLQA provenance is claimed.",
                        "LLM-judge estimates are available, with human calibration pending; no public VLQA provenance is claimed.")
    text = text.replace("semantic collection is complete", "native collection is complete")
    text = text.replace("semantic validation and rehearsal remain outstanding.", "human validation and rehearsal remain outstanding.")
    text = text.replace("pending validated semantic judging, team confirmations and demo rehearsal.", "pending human validation of judge estimates, team confirmations and demo rehearsal.")
    text = text.replace("Native measurements are collected on the Mac under the frozen protocol.",
                        "DeepSeek Flash was also used through the gateway for independent semantic evaluation; its outputs are AI judgments, not member verification or human labels. Native measurements were collected on the Mac under the frozen protocol.")
    data = json.loads(Path(summary_path).read_text())
    if data.get("recovery"):
        text = text.replace("and at most two retained attempts per output;", "and at most two initial attempts per output, with a separately disclosed streamed recovery for invalid judgments;")
    report.write_text(text)
    native = Path("deliverables/d2/report/native_results.tex")
    text = native.read_text().replace("Semantic task success", "Human-validated task success")
    text = text.replace("Claim support / unsupported rate", "Human-validated support rate")
    text = text.replace(r"\pending{judge / human audit}", r"\pending{human audit}")
    native.write_text(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    update(args.summary)
