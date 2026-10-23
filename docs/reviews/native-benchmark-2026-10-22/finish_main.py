"""Finish this already-running collection; never launch or retry inference batches.

Run from the repository root. This is a one-shot continuation of main-v2, not
a scheduler. Semantic judging and human labels are deliberately not generated.
"""
import json
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
RUN = Path("evaluation/runs/bll2019-main-v2")
EVIDENCE = Path("docs/reviews/native-benchmark-2026-10-22")
PYTHON = str(ROOT / ".venv/bin/python")
TASKS = "evaluation/benchmarks/bll2019_v1/tasks.json"


def main():
    state = {"started_at": datetime.now(timezone.utc).isoformat(), "steps": [],
             "semantic_judging_executed": False, "human_labels_created": False}
    receipt = EVIDENCE / "completion-pipeline.json"

    def save():
        receipt.write_text(json.dumps(state, indent=2) + "\n")

    def command(label, args):
        with (EVIDENCE / "logs" / (label + ".log")).open("x") as stream:
            result = subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        state["steps"].append({"name": label, "returncode": result.returncode})
        save()
        if result.returncode:
            raise RuntimeError(label + " failed; see retained log")

    try:
        save()
        deadline = time.monotonic() + 4 * 3600
        while True:
            manifest = json.loads((RUN / "manifest.json").read_text())
            if manifest["status"] == "collected_pending_human_scoring":
                break
            if manifest["status"] != "collecting":
                raise RuntimeError("Collection is incomplete; no main table produced")
            if time.monotonic() > deadline:
                raise RuntimeError("Collection did not finish within continuation deadline")
            time.sleep(5)
        command("main-analysis", [PYTHON, "-m", "evaluation.analyze_native", "--run-dir", str(RUN),
                                  "--tasks", TASKS, "--output", str(RUN / "operational-summary.json")])
        command("main-blind-export", [PYTHON, "-m", "evaluation.export_blind_review", "--run-dir", str(RUN),
                                      "--output", str(RUN / "blind-review")])
        command("main-table", [PYTHON, "-m", "evaluation.render_native_table", "--run-dir", str(RUN),
                               "--tasks", TASKS, "--output", "report_d2/native_results.tex"])
        command("post-main-real-tests", [PYTHON, "-m", "pytest", "tests/", "-q"])
        report = Path("report_d2/main_d2.tex")
        content = report.read_text().replace(
            "native evaluation is underway; semantic validation and rehearsal remain outstanding.",
            "native collection is complete; semantic validation and rehearsal remain outstanding.")
        report.write_text(content)
        command("post-main-report-build", ["make", "report_d2"])
        target = Path("tmp/pdfs/d2-post-main")
        target.mkdir(parents=True, exist_ok=True)
        command("post-main-report-render", ["pdftoppm", "-scale-to", "1200", "-png",
                                           "report_d2/main_d2.pdf", str(target / "page")])
        state.update(status="operational_artifacts_ready_pending_visual_review_and_semantic_validation",
                     completed_at=datetime.now(timezone.utc).isoformat())
        save()
    except Exception as exc:
        state.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        save()
        raise


if __name__ == "__main__":
    main()
