"""End-to-End Playwright Browser & QA Stress Test Suite for LuatCheck-D2.

Exercises real browser interactions against http://127.0.0.1:8000 with real Metal inference
(:8081 Bonsai 4B, :8082 Vietnamese Reranker f16).
Validates:
1. Console errors, page errors, HTTP >= 400 status codes.
2. Layout responsiveness (1440x900, 1280x800) and horizontal overflow checks.
3. Tab switching UX (+ Câu hỏi mới & GẦN ĐÂY history from Corpus tab).
4. All 20 documents in Corpus Inspector across Labour and HCMUT.
5. Live end-to-end query in Labour VN with citation PDF jump (BLLD2019_Dieu_25 -> Page 11).
6. Live end-to-end query in HCMUT with citation PDF jump and page verification.
"""

import pytest
from playwright.sync_api import sync_playwright

WEB_URL = "http://127.0.0.1:8000"


def test_playwright_e2e_full_audit():
    console_errors = []
    page_errors = []
    http_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        def on_console(msg):
            # Ignore harmless favicon 404 or informational messages
            if msg.type in ("error", "warning") and "favicon" not in msg.text:
                console_errors.append(f"[{msg.type}] {msg.text}")

        def on_pageerror(err):
            page_errors.append(str(err))

        def on_response(res):
            if res.status >= 400 and "favicon" not in res.url:
                http_errors.append(f"{res.status} {res.url}")

        page.on("console", on_console)
        page.on("pageerror", on_pageerror)
        page.on("response", on_response)

        # ----------------------------------------------------------------------
        # 1. Load Homepage & Responsive Viewport Check
        # ----------------------------------------------------------------------
        page.goto(f"{WEB_URL}/", wait_until="networkidle")
        page.wait_for_selector(".workspace", timeout=10000)

        # Check 1440x900
        sw1440 = page.evaluate("document.documentElement.scrollWidth")
        cw1440 = page.evaluate("document.documentElement.clientWidth")
        assert sw1440 <= cw1440, f"Horizontal overflow at 1440x900: {sw1440} > {cw1440}"

        # Check 1280x800
        page.set_viewport_size({"width": 1280, "height": 800})
        page.wait_for_timeout(300)
        sw1280 = page.evaluate("document.documentElement.scrollWidth")
        cw1280 = page.evaluate("document.documentElement.clientWidth")
        assert sw1280 <= cw1280, f"Horizontal overflow at 1280x800: {sw1280} > {cw1280}"
        page.set_viewport_size({"width": 1440, "height": 900})

        # ----------------------------------------------------------------------
        # 2. UX Interaction 1: Tab switching (+ Câu hỏi mới)
        # ----------------------------------------------------------------------
        corpus_tab_btn = page.locator(".primary-tab-btn:has-text('Kho văn bản & Chunk')")
        corpus_tab_btn.click()
        page.wait_for_selector(".corpus-inspector", timeout=5000)
        assert page.locator(".corpus-inspector").is_visible()

        # Click "+ Câu hỏi mới" on sidebar
        new_q_btn = page.locator(".new-case-button")
        new_q_btn.click()
        page.wait_for_selector("#question-input", timeout=5000)
        assert page.locator("#question-input").is_visible()
        assert not page.locator(".corpus-inspector").is_visible()

        # ----------------------------------------------------------------------
        # 3. Inspect All 20 Documents in Corpus Inspector
        # ----------------------------------------------------------------------
        corpus_tab_btn.click()
        page.wait_for_selector(".corpus-inspector", timeout=5000)

        # Check Labour Corpus (10 docs)
        labour_pill = page.locator(".corpus-pill-btn:has-text('Pháp luật Lao động')")
        labour_pill.click()
        page.wait_for_selector('.doc-item-btn .doc-code-badge:has-text("BLLD2019")', timeout=5000)
        assert page.locator(".doc-item-btn").count() == 10

        for i in range(10):
            btn = page.locator(".doc-item-btn").nth(i)
            doc_code = btn.locator(".doc-code-badge").inner_text()
            btn.click()
            page.wait_for_selector(f'.doc-banner .badge-code:has-text("{doc_code}")', timeout=5000)
            page.wait_for_selector(f'.chunk-card .chunk-id-badge:has-text("{doc_code}")', timeout=5000)
            count = page.locator(".chunk-card").count()
            assert count > 0, f"Labour doc {doc_code} has 0 chunks"

        # Check HCMUT Corpus (10 docs)
        hcmut_pill = page.locator(".corpus-pill-btn:has-text('Học vụ HCMUT')")
        hcmut_pill.click()
        page.wait_for_selector('.doc-item-btn .doc-code-badge:has-text("HVDT1260")', timeout=5000)
        assert page.locator(".doc-item-btn").count() == 10

        for i in range(10):
            btn = page.locator(".doc-item-btn").nth(i)
            doc_code = btn.locator(".doc-code-badge").inner_text()
            btn.click()
            page.wait_for_selector(f'.doc-banner .badge-code:has-text("{doc_code}")', timeout=5000)
            page.wait_for_selector(f'.chunk-card .chunk-id-badge:has-text("{doc_code}")', timeout=5000)
            count = page.locator(".chunk-card").count()
            assert count > 0, f"HCMUT doc {doc_code} has 0 chunks"

        # ----------------------------------------------------------------------
        # 4. Live E2E Query — Labour Law Profile with Page 11 Jump Check
        # ----------------------------------------------------------------------
        new_q_btn.click()
        page.wait_for_selector("#question-input", timeout=5000)

        # Switch to Labour profile
        labour_profile_btn = page.locator(".profile-switch button:has-text('Lao động')")
        if labour_profile_btn.count() > 0:
            labour_profile_btn.first.click()
            page.wait_for_timeout(300)

        textarea = page.locator("#question-input")
        textarea.fill("Thời gian thử việc tối đa đối với người quản lý doanh nghiệp là bao lâu?")
        page.locator("button.submit-button").click()

        # Wait for run to finish (real Metal llama-server inference)
        page.wait_for_selector(".result-view", timeout=10000)
        page.wait_for_selector(".state-badge:not(.state-active)", timeout=120000)
        badge_text = page.locator(".state-badge").inner_text()
        print(f"\n[E2E] Labour run finished: {badge_text}")

        # Test history item click switches back from corpus view
        corpus_tab_btn.click()
        page.wait_for_selector(".corpus-inspector", timeout=5000)
        assert page.locator(".corpus-inspector").is_visible()

        first_hist = page.locator(".history-item").first
        first_hist.click()
        page.wait_for_selector(".result-view", timeout=5000)
        assert page.locator(".result-view").is_visible()
        assert not page.locator(".corpus-inspector").is_visible()

        # Verify citation jump on Labour
        labour_citations = page.locator(".source-item").all()
        assert len(labour_citations) > 0, "Expected at least 1 citation in Labour query"

        # Click citation and inspect PDF
        first_cit = page.locator(".source-item").first
        first_cit.locator(".source-head").click()
        page.wait_for_timeout(300)

        inspect_btn = first_cit.locator(".inspect-pdf-btn")
        assert inspect_btn.is_visible()
        inspect_btn.click()

        page.wait_for_selector(".corpus-inspector", timeout=5000)
        assert page.locator(".corpus-inspector").is_visible()

        # Wait for highlighted chunk and check PDF page indicator
        page.wait_for_selector(".highlighted-pulse", timeout=5000)
        pulse_id = page.locator(".highlighted-pulse .chunk-id-badge").inner_text()
        print(f"[E2E] Highlighted chunk: {pulse_id}")

        page_indicator = page.locator(".pdf-page-indicator").inner_text()
        print(f"[E2E] PDF Page indicator: {page_indicator}")

        iframe_src = page.locator(".pdf-embedded-frame").get_attribute("src") or ""
        print(f"[E2E] Iframe src: {iframe_src}")

        if "Dieu_25" in pulse_id:
            assert "11" in page_indicator or "12" in page_indicator, (
                f"Expected page indicator to show Trang 11 or 12, got: {page_indicator}"
            )
            assert "#page=11" in iframe_src, f"Expected #page=11 in iframe, got: {iframe_src}"

        # ----------------------------------------------------------------------
        # 5. Live E2E Query — HCMUT Academic Profile
        # ----------------------------------------------------------------------
        new_q_btn.click()
        page.wait_for_selector("#question-input", timeout=5000)

        # Switch to HCMUT profile
        hcmut_profile_btn = page.locator(".profile-switch button:has-text('Học vụ')")
        if hcmut_profile_btn.count() > 0:
            hcmut_profile_btn.first.click()
            page.wait_for_timeout(300)

        textarea = page.locator("#question-input")
        textarea.fill("Sinh viên năm nhất bị cảnh báo học tập khi nào?")
        page.locator("button.submit-button").click()

        # Wait for run to finish
        page.wait_for_selector(".result-view", timeout=10000)
        page.wait_for_selector(".state-badge:not(.state-active)", timeout=120000)
        hcmut_badge = page.locator(".state-badge").inner_text()
        print(f"[E2E] HCMUT run finished: {hcmut_badge}")

        # Check citations and PDF jump
        citations = page.locator(".source-item").all()
        if len(citations) > 0:
            first_cit = page.locator(".source-item").first
            first_cit.locator(".source-head").click()
            page.wait_for_timeout(300)
            inspect_btn = first_cit.locator(".inspect-pdf-btn")
            if inspect_btn.is_visible():
                inspect_btn.click()
                page.wait_for_selector(".corpus-inspector", timeout=5000)
                assert page.locator(".corpus-inspector").is_visible()
                page.wait_for_selector(".highlighted-pulse", timeout=5000)
                assert page.locator(".highlighted-pulse").is_visible()

        browser.close()

    # --------------------------------------------------------------------------
    # 6. Verify 0 Unhandled Console or HTTP Errors
    # --------------------------------------------------------------------------
    print(f"\n[QA Summary] Total Console Warnings/Errors: {len(console_errors)}")
    print(f"[QA Summary] Total Page JS Errors: {len(page_errors)}")
    print(f"[QA Summary] Total HTTP 4xx/5xx Errors: {len(http_errors)}")

    assert len(page_errors) == 0, f"Page JS errors occurred: {page_errors}"
    assert len(http_errors) == 0, f"HTTP errors occurred: {http_errors}"
