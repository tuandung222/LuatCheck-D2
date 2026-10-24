"""Record demo scenarios from the real web UI (headless Chromium via Playwright, then ffmpeg).

Every recording drives the running UI like a person: it picks the corpus, types the question, presses Enter and waits
for the real run (Bonsai controller on :8081, reranker on :8082) to finish. Nothing is pre-recorded or mocked, and a
failed or odd outcome is recorded as it is.

Requirements (repo .venv only; the browser binary goes to the user-level Playwright cache):
    .venv/bin/pip install playwright && .venv/bin/python -m playwright install chromium
    /opt/homebrew/bin/ffmpeg
Usage:
    make demo-web   # in another terminal, servers 8081/8082 running
    .venv/bin/python docs/presentation/record_demo.py --base http://127.0.0.1:8000 --only 01 02
Outputs: docs/presentation/gifs/<id>.gif (+ <id>.mp4 kept in --work) and docs/presentation/gifs/demo_backup.mp4
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

FFMPEG = "/opt/homebrew/bin/ffmpeg"
ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_FILE = Path(__file__).with_name("demo_scenarios.json")


def convert(webm: Path, gif: Path, mp4: Path, trim_start: float, gif_width: int, fps: int) -> None:
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", str(trim_start), "-i", str(webm), "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "23", "-preset", "medium", "-r", "25", "-an", str(mp4)], check=True)
    palette = (f"fps={fps},scale={gif_width}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];"
               f"[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(mp4), "-vf", palette, "-loop", "0", str(gif)], check=True)


def record(play: Any, default_base: str, scenario: Dict[str, Any], work: Path, width: int, height: int) -> Dict[str, Any]:
    base = scenario.get("base", default_base)
    browser = play.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": width, "height": height}, record_video_dir=str(work),
                                  record_video_size={"width": width, "height": height}, locale="vi-VN")
    page = context.new_page()
    console_errors: List[str] = []
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    t_open = time.time()
    page.goto(base)
    page.wait_for_selector(".system-strip .fact b")
    page.wait_for_timeout(1200)
    trim_start = max(0.0, time.time() - t_open - 0.6)  # drop the blank page-load frames
    radio = page.get_by_role("radio", name=scenario["profile_label"]) if scenario.get("profile_label") else None
    if radio is not None and radio.count():  # a single-profile instance has no corpus switch
        radio.click()
        page.wait_for_timeout(900)
    if scenario.get("mode") == "off":
        page.select_option("select[aria-label='Chế độ kiểm tra']", "off")
        page.wait_for_timeout(600)
    box = page.locator("#question-input")
    box.click()
    box.type(scenario["query"], delay=14)
    page.wait_for_timeout(700)
    t_submit = time.time()
    page.keyboard.press("Enter")
    page.wait_for_selector(".working, .outcome", timeout=15000)
    page.wait_for_selector(".outcome", timeout=240000)
    run_seconds = time.time() - t_submit
    page.wait_for_timeout(2500)
    action = scenario.get("after")
    if action == "open_citation" and page.locator(".answer-cites button").count():
        page.locator(".answer-cites button").first.click()
        page.wait_for_timeout(3500)
    elif action == "show_repairs" and page.locator(".step-line", has_text="Sửa chữa").count():
        page.locator(".step-line", has_text="Sửa chữa").first.scroll_into_view_if_needed()  # repair steps are below the fold
        page.wait_for_timeout(4500)
    elif action == "open_retrieved" and page.locator(".retrieved-toggle").count():
        page.locator(".retrieved-toggle").click()
        page.wait_for_timeout(800)
        page.locator(".source-head").first.click()
        page.wait_for_timeout(3500)
    else:
        page.wait_for_timeout(2500)
    repair_steps = page.locator(".step-line", has_text="Sửa chữa").count()
    state = page.locator(".state-badge").first.inner_text()
    outcome_title = page.locator(".outcome > header b").first.inner_text()
    total = page.locator(".timeline-total b").inner_text()
    video = page.video.path()
    context.close()
    browser.close()
    return {"video": str(video), "trim_start": trim_start, "run_seconds": round(run_seconds, 1), "state": state,
            "outcome": outcome_title, "ui_total": total, "repair_steps": repair_steps,
            "console_errors": console_errors}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--work", default=str(Path(tempfile.gettempdir()) / "luatcheck_demo_recordings"))
    ap.add_argument("--out", default=str(Path(__file__).with_name("gifs")))
    ap.add_argument("--only", nargs="*", help="scenario id prefixes")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--gif-width", type=int, default=1000)
    ap.add_argument("--fps", type=int, default=8)
    ap.add_argument("--no-concat", action="store_true")
    ap.add_argument("--scenarios", default=str(SCENARIOS_FILE), help="scenario JSON file (default: demo_scenarios.json)")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    scenarios = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))
    if args.only:
        scenarios = [s for s in scenarios if any(s["id"].startswith(p) for p in args.only)]
    work, out = Path(args.work), Path(args.out)
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    report = []
    with sync_playwright() as play:
        for scenario in scenarios:
            print(f"recording {scenario['id']} ...", flush=True)
            # A scenario may name the UI state it demonstrates (the error scenario needs the controller to call search
            # before the failing reranker is reached). Attempts that end in another state are not used, and said so.
            for attempt in range(1, int(scenario.get("max_attempts", 1)) + 1):
                result = record(play, args.base, scenario, work, args.width, args.height)
                result["attempt"] = attempt
                state_ok = not scenario.get("expect_state") or result["state"] == scenario["expect_state"]
                repair_ok = not scenario.get("require_repair") or result["repair_steps"] > 0
                if state_ok and repair_ok:
                    break
                print(f"  attempt {attempt}: state {result['state']!r}, repair steps {result['repair_steps']}; wanted state "
                      f"{scenario.get('expect_state')!r}, repair {bool(scenario.get('require_repair'))}; retrying", flush=True)
            mp4 = work / f"{scenario['id']}.mp4"
            gif = out / f"{scenario['id']}.gif"
            convert(Path(result["video"]), gif, mp4, result["trim_start"], args.gif_width, args.fps)
            result.update(id=scenario["id"], gif_mb=round(gif.stat().st_size / 1e6, 2))
            report.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    (work / "last_recording_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    if report and not args.no_concat:
        listing = work / "concat.txt"
        clips = sorted(work.glob("[0-9][0-9]_*.mp4"))
        listing.write_text("".join(f"file '{c}'\n" for c in clips), encoding="utf-8")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy",
                        str(out / "demo_backup.mp4")], check=True)
        print("wrote", out / "demo_backup.mp4", round((out / "demo_backup.mp4").stat().st_size / 1e6, 2), "MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
