#!/usr/bin/env python3
"""
E2E test for Module Upload with journal extraction only.

This is faster than full pipeline (~2 minutes vs 20+ minutes).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from foundry_helper import FoundrySession

TEST_PDF = Path(__file__).parent.parent.parent.parent.parent / "data/pdfs/Lost_Mine_of_Phandelver_test.pdf"


def run_test(headless: bool = True):
    print("=" * 60)
    print("MODULE UPLOAD E2E TEST (Journal Only)")
    print("=" * 60)
    print()

    if not TEST_PDF.exists():
        print(f"ERROR: Test PDF not found at {TEST_PDF}")
        return False

    print(f"Using test PDF: {TEST_PDF.name}")
    print()

    with FoundrySession(headless=headless) as session:
        page = session.page

        # Navigate to Module tab
        print("[1/7] Navigating to Module tab...")
        session.goto_tablewrite()
        time.sleep(1)
        page.locator('.tablewrite-tabs .tab-btn[data-tab="module"]').click()
        time.sleep(0.5)
        print("  OK")

        # Upload PDF
        print("[2/7] Uploading PDF...")
        page.locator('#module-file').set_input_files(str(TEST_PDF))
        time.sleep(0.5)
        print("  OK: File selected")

        # Uncheck all options except Journal
        print("[3/7] Configuring options (journal only)...")
        page.locator('#opt-actors').uncheck()
        page.locator('#opt-maps').uncheck()
        page.locator('#opt-artwork').uncheck()
        time.sleep(0.2)

        # Verify only journal is checked
        assert page.locator('#opt-journal').is_checked(), "Journal should be checked"
        assert not page.locator('#opt-actors').is_checked(), "Actors should be unchecked"
        assert not page.locator('#opt-maps').is_checked(), "Maps should be unchecked"
        assert not page.locator('#opt-artwork').is_checked(), "Artwork should be unchecked"
        print("  OK: Only journal extraction enabled")

        # Take screenshot before import
        page.locator('#sidebar').screenshot(path='/tmp/module_journal_before.png')

        # Click Import
        print("[4/7] Clicking Import...")
        page.locator('#import-module-btn').click()
        time.sleep(1)

        # Verify progress showing
        progress = page.locator('#module-tab .progress-container')
        if progress.count() > 0:
            print("  OK: Progress visible")

        # Wait for completion (up to 5 minutes for journal-only)
        print("[5/7] Waiting for processing (up to 5 minutes)...")
        max_wait = 300
        elapsed = 0

        while elapsed < max_wait:
            result = page.locator('#module-tab .result-container')
            if result.count() > 0:
                display = result.evaluate('el => getComputedStyle(el).display')
                if display != 'none':
                    print(f"  Complete after {elapsed}s")
                    break

            # Check for error
            error = page.locator('.notification.error')
            if error.count() > 0:
                error_text = error.first.text_content()
                print(f"  ERROR: {error_text}")
                page.locator('#sidebar').screenshot(path='/tmp/module_journal_error.png')
                return False

            if elapsed % 30 == 0:
                status = page.locator('#module-tab #progress-status')
                if status.count() > 0:
                    print(f"    [{elapsed}s] {status.text_content()}")

            time.sleep(5)
            elapsed += 5

        if elapsed >= max_wait:
            print(f"  TIMEOUT after {max_wait}s")
            page.locator('#sidebar').screenshot(path='/tmp/module_journal_timeout.png')
            return False

        # Verify results
        print("[6/7] Verifying results...")

        summary = page.locator('#module-tab #result-summary')
        if summary.count() > 0:
            text = summary.text_content()
            print(f"  Summary: {text[:100]}...")

            if "Import Complete" in text or "import complete" in text.lower():
                print("  OK: Import Complete message found")
            else:
                print("  WARNING: No 'Import Complete' message")

        # Check for journal link
        journal_link = page.locator('#module-tab .content-link[data-uuid*="JournalEntry"]')
        if journal_link.count() > 0:
            uuid = journal_link.first.get_attribute('data-uuid')
            print(f"  OK: Journal UUID: {uuid}")
        else:
            print("  WARNING: No journal link found")

        # Take final screenshot
        print("[7/7] Saving screenshot...")
        page.locator('#sidebar').screenshot(path='/tmp/module_journal_result.png')
        print("  Saved: /tmp/module_journal_result.png")

        print()
        print("=" * 60)
        print("TEST PASSED")
        print("=" * 60)
        return True


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--visible', action='store_true')
    args = parser.parse_args()

    success = run_test(headless=not args.visible)
    sys.exit(0 if success else 1)
