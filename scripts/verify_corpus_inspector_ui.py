"""Playwright verification script for Corpus & PDF Chunk Inspector."""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("/Users/admin/.gemini/antigravity/brain/e93f115f-b3a3-451e-a114-6f01ff292b30/scratch/qa-frontend-2026-10-26/corpus-inspector")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

URL = "http://127.0.0.1:8000"


def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("1. Navigating to", URL)
        page.goto(URL, wait_until="networkidle")
        time.sleep(1)

        # Verify initial page loaded
        page.screenshot(path=str(OUTPUT_DIR / "00_initial_qa_view.png"))
        print("  -> Saved 00_initial_qa_view.png")

        # 2. Click "Kho văn bản & Chunk" navigation tab
        print("2. Clicking 'Kho văn bản & Chunk' primary tab")
        tab_btn = page.locator("button.primary-tab-btn:has-text('Kho văn bản & Chunk')")
        assert tab_btn.is_visible(), "Corpus Inspector tab button not visible in topbar!"
        tab_btn.click()
        time.sleep(1.5)

        # Verify Corpus Inspector is visible
        inspector = page.locator(".corpus-inspector")
        assert inspector.is_visible(), "Corpus Inspector view not visible after clicking tab!"

        page.screenshot(path=str(OUTPUT_DIR / "01_corpus_inspector_initial_overview.png"))
        print("  -> Saved 01_corpus_inspector_initial_overview.png")

        # 3. Switch to Labour Corpus to verify BLLD2019
        print("3. Switching to 'Pháp luật Lao động' Corpus")
        labour_btn = page.locator("button.corpus-pill-btn:has-text('Pháp luật Lao động')")
        assert labour_btn.is_visible()
        labour_btn.click()
        time.sleep(1.5)

        # Check BLLD2019 split view
        pdf_iframe = page.locator("iframe.pdf-embedded-frame")
        assert pdf_iframe.is_visible(), "PDF iframe not visible in Pane A!"
        iframe_src = pdf_iframe.get_attribute("src")
        print("  -> Labour PDF iframe src:", iframe_src)
        assert "/api/corpus/pdf/labour/BLLD2019" in iframe_src

        # Check Chunks list
        chunk_cards = page.locator(".chunk-card")
        chunk_count = chunk_cards.count()
        print(f"  -> Pane B rendered {chunk_count} chunk cards for BLLD2019")
        assert chunk_count > 0, "No chunks rendered in Pane B!"

        page.screenshot(path=str(OUTPUT_DIR / "02_labour_bll2019_split_view.png"))
        print("  -> Saved 02_labour_bll2019_split_view.png")

        # 4. Test Search filter in Pane B for "thử việc"
        print("4. Testing Search Filter in Pane B ('thử việc')")
        search_input = page.locator(".search-box input")
        search_input.fill("thử việc")
        time.sleep(0.5)

        filtered_cards = page.locator(".chunk-card")
        filtered_count = filtered_cards.count()
        print(f"  -> Filtered cards count for 'thử việc': {filtered_count}")
        assert filtered_count >= 1, "Expected filtered chunk cards for 'thử việc'!"

        page.screenshot(path=str(OUTPUT_DIR / "03_chunks_filter_search.png"))
        print("  -> Saved 03_chunks_filter_search.png")

        # Clear search
        page.locator("button.clear-search-btn").click()
        time.sleep(0.5)

        # 5. Switch to HCMUT Corpus
        print("5. Switching to HCMUT Corpus ('Học vụ HCMUT')")
        hcmut_btn = page.locator("button.corpus-pill-btn:has-text('Học vụ HCMUT')")
        hcmut_btn.click()
        time.sleep(1.5)

        # Verify HCMUT docs
        doc_sidebar_items = page.locator(".doc-item-btn")
        print(f"  -> HCMUT docs count in sidebar: {doc_sidebar_items.count()}")
        assert doc_sidebar_items.count() == 10

        page.screenshot(path=str(OUTPUT_DIR / "04_corpus_inspector_hcmut.png"))
        print("  -> Saved 04_corpus_inspector_hcmut.png")

        # 6. Click NOIQUY1924 in HCMUT
        print("6. Selecting NOIQUY1924 document")
        noiquy_btn = page.locator(".doc-item-btn:has-text('NOIQUY1924')")
        assert noiquy_btn.is_visible()
        noiquy_btn.click()
        time.sleep(1.5)

        noiquy_iframe = page.locator("iframe.pdf-embedded-frame")
        print("  -> NOIQUY1924 iframe src:", noiquy_iframe.get_attribute("src"))
        assert "NOIQUY1924" in noiquy_iframe.get_attribute("src")

        page.screenshot(path=str(OUTPUT_DIR / "05_hcmut_noiquy_document.png"))
        print("  -> Saved 05_hcmut_noiquy_document.png")

        # 7. Test Verbatim vs Formatted toggle
        print("7. Testing Verbatim View Mode")
        verbatim_btn = page.locator("button.mode-btn:has-text('Thô')")
        verbatim_btn.click()
        time.sleep(0.5)
        page.screenshot(path=str(OUTPUT_DIR / "06_chunk_verbatim_view.png"))
        print("  -> Saved 06_chunk_verbatim_view.png")

        # Switch back to formatted
        page.locator("button.mode-btn:has-text('Định dạng')").click()
        time.sleep(0.5)

        # 8. Test selecting another labour document: ND293_2025
        print("8. Testing ND293_2025 document selection")
        page.locator("button.corpus-pill-btn:has-text('Pháp luật Lao động')").click()
        time.sleep(1)
        nd293_doc = page.locator(".doc-item-btn:has-text('ND293_2025')")
        nd293_doc.click()
        time.sleep(1)

        page.screenshot(path=str(OUTPUT_DIR / "07_nd293_2025_selected.png"))
        print("  -> Saved 07_nd293_2025_selected.png")

        # Return to QA View
        page.locator("button.primary-tab-btn:has-text('Hỏi đáp & Thẩm định')").click()
        time.sleep(0.8)
        page.screenshot(path=str(OUTPUT_DIR / "08_back_to_qa_view.png"))
        print("  -> Saved 08_back_to_qa_view.png")

        browser.close()
        print("\nAll Playwright UI verifications PASSED!")


if __name__ == "__main__":
    run_verification()
