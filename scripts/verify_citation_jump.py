"""Playwright script to verify Citation Drawer -> Corpus Inspector Jump feature."""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("/Users/admin/.gemini/antigravity/brain/e93f115f-b3a3-451e-a114-6f01ff292b30/scratch/qa-frontend-2026-10-26/corpus-inspector")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

URL = "http://127.0.0.1:8000"


def run_citation_jump_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--headless=new"])
        context = browser.new_context(viewport={"width": 1440, "height": 900})

        # Set session cookie to match demo run session
        context.add_cookies([{
            "name": "luatcheck_session",
            "value": "demo_session_123",
            "domain": "127.0.0.1",
            "path": "/",
        }])

        page = context.new_page()
        print("1. Navigating with demo session...")
        page.goto(URL, wait_until="networkidle")
        time.sleep(1.5)

        # 2. Click the demo run in history
        history_item = page.locator(".history-item:has-text('Thời gian thử việc tối đa')")
        assert history_item.is_visible(), "Demo run not visible in history!"
        print("2. Clicking history item...")
        history_item.click()
        time.sleep(1.5)

        # 3. Verify Answer Card & Citation pill
        cite_pill = page.locator(".answer-cites button:has-text('BLLD2019_Dieu_25')")
        assert cite_pill.is_visible(), "Citation pill BLLD2019_Dieu_25 not visible!"
        print("3. Clicking citation pill...")
        cite_pill.click()
        time.sleep(1)

        # 4. Check SourceItem is open and "Xem file PDF gốc & Chunk" button is present
        inspect_btn = page.locator(".inspect-pdf-btn:has-text('Xem file PDF gốc & Chunk')")
        assert inspect_btn.is_visible(), "Button 'Xem file PDF gốc & Chunk' not found in source item!"
        print("4. Source Item open. Taking screenshot of Citation Drawer...")
        page.screenshot(path=str(OUTPUT_DIR / "09_citation_drawer_with_button.png"))
        print("  -> Saved 09_citation_drawer_with_button.png")

        # 5. Click the "Xem file PDF gốc & Chunk" button
        print("5. Clicking 'Xem file PDF gốc & Chunk' button...")
        inspect_btn.click()
        time.sleep(2)

        # 6. Verify view switched to Corpus Inspector
        inspector = page.locator(".corpus-inspector")
        assert inspector.is_visible(), "View did not switch to Corpus Inspector!"

        # Verify selected document is BLLD2019
        active_doc = page.locator(".doc-item-btn.active .doc-code-badge")
        print("  -> Active document badge:", active_doc.text_content())
        assert active_doc.text_content() == "BLLD2019"

        # Verify highlighted chunk is BLLD2019_Dieu_25
        highlighted_card = page.locator(".chunk-card.highlighted-pulse")
        assert highlighted_card.is_visible(), "Target chunk is not highlighted!"
        chunk_badge = highlighted_card.locator(".chunk-id-badge")
        print("  -> Highlighted chunk ID:", chunk_badge.text_content())
        assert "BLLD2019_Dieu_25" in chunk_badge.text_content()

        page.screenshot(path=str(OUTPUT_DIR / "10_citation_jump_to_chunk_highlighted.png"))
        print("  -> Saved 10_citation_jump_to_chunk_highlighted.png")

        browser.close()
        print("\nCitation Jump Integration PASSED 100%!")


if __name__ == "__main__":
    run_citation_jump_verification()
