"""One-shot continuation of the authorized DeepSeek judging batch."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
RUN = Path("evaluation/runs/deepseek-judge-main-v1")
BLIND = "evaluation/runs/bll2019-main-v2/blind-review"
OUTPUT = RUN / "analysis"
EVIDENCE = Path("docs/reviews/deepseek-judge-2026-10-22")
PYTHON = str(ROOT / ".venv/bin/python")


def main():
    receipt = {"status": "waiting_for_judge", "steps": [], "human_labels_created": False}
    def save():
        (EVIDENCE / "completion.json").write_text(json.dumps(receipt, indent=2) + "\n")
    def command(name, args):
        with (EVIDENCE / (name + ".log")).open("x") as stream:
            result = subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        receipt["steps"].append({"name": name, "returncode": result.returncode})
        save()
        if result.returncode:
            raise RuntimeError(name + " failed; preserve logs")
    try:
        save()
        end = time.monotonic() + 3 * 3600
        while True:
            try:
                manifest = json.loads((RUN / "manifest.json").read_text())
            except json.JSONDecodeError:
                time.sleep(1)
                continue
            if manifest["status"] == "collected_pending_human_validation":
                break
            if manifest["status"] != "collecting" or time.monotonic() > end:
                raise RuntimeError("Judge batch incomplete or deadline exceeded")
            time.sleep(5)
        analysis_args = [PYTHON, "-m", "evaluation.analyze_judge", "--judge-dir", str(RUN),
                         "--blind-dir", BLIND, "--output", str(OUTPUT)]
        if manifest.get("invalid", 0):
            recovery = Path("evaluation/runs/deepseek-judge-recovery-v1")
            command("schema-recovery", [PYTHON, "-m", "evaluation.recover_judge", "--main-dir", str(RUN),
                                        "--output", str(recovery), "--execute"])
            analysis_args += ["--recovery-dir", str(recovery)]
        command("analysis", analysis_args)
        command("report-insertion", [PYTHON, "-m", "evaluation.report_judge", "--summary", str(OUTPUT / "summary.json")])
        command("non-native-tests-final", [PYTHON, "-m", "pytest", "tests/test_real_system.py", "-q", "-k", "not native"])
        command("report-build", ["make", "report_d2"])
        images = Path("tmp/pdfs/d2-with-judge")
        images.mkdir(parents=True, exist_ok=True)
        command("report-render", ["pdftoppm", "-scale-to", "1200", "-png", "report_d2/main_d2.pdf", str(images / "page")])
        receipt.update(status="llm_estimates_ready_pending_visual_review_and_human_audit",
                       completed_at=datetime.now(timezone.utc).isoformat())
        save()
    except Exception as exc:
        receipt.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        save()
        raise


if __name__ == "__main__":
    main()
