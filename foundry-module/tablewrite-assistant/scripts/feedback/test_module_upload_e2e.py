#!/usr/bin/env python3
"""
End-to-end test for Module Upload functionality.

This test actually uploads a PDF and verifies the results are displayed.

Usage:
    python test_module_upload_e2e.py [--visible]
"""

import sys
import time
import argparse
from pathlib import Path

# Add parent to path for foundry_helper import
sys.path.insert(0, str(Path(__file__).parent))
from foundry_helper import FoundrySession

# Path to test PDF
TEST_PDF = Path(__file__).parent.parent.parent.parent.parent / "data/pdfs/Lost_Mine_of_Phandelver_test.pdf"


def run_e2e_test(headless: bool = True):
    """Run end-to-end Module upload test."""
    print("=" * 60)
    print("MODULE UPLOAD END-TO-END TEST")
    print("=" * 60)
    print()

    if not TEST_PDF.exists():
        print(f"ERROR: Test PDF not found at {TEST_PDF}")
        return False

    print(f"Using test PDF: {TEST_PDF}")
    print(f"File size: {TEST_PDF.stat().st_size / 1024:.1f} KB")
    print()

    with FoundrySession(headless=headless) as session:
        page = session.page

        # Step 1: Navigate to Tablewrite tab
        print("[1/6] Navigating to Tablewrite tab...")
        session.goto_tablewrite()
        time.sleep(1)

        # Step 2: Click Module tab
        print("[2/6] Clicking Module tab...")
        module_btn = page.locator('.tablewrite-tabs .tab-btn[data-tab="module"]')
        if module_btn.count() == 0:
            print("  FAIL: Module tab button not found")
            return False
        module_btn.click()
        time.sleep(0.5)

        # Verify module tab is visible
        module_tab = page.locator('#module-tab')
        if module_tab.evaluate('el => getComputedStyle(el).display') == 'none':
            print("  FAIL: Module tab content not visible")
            return False
        print("  OK: Module tab visible")

        # Step 3: Upload the PDF file
        print("[3/6] Uploading test PDF...")
        file_input = page.locator('#module-file')
        if file_input.count() == 0:
            print("  FAIL: File input not found")
            return False

        file_input.set_input_files(str(TEST_PDF))
        time.sleep(0.5)

        # Verify file was selected
        file_display = page.locator('#file-name-display')
        if file_display.count() > 0:
            displayed_name = file_display.text_content()
            print(f"  OK: File selected - '{displayed_name}'")

        # Verify import button is now enabled
        import_btn = page.locator('#import-module-btn')
        if import_btn.is_disabled():
            print("  FAIL: Import button still disabled after file selection")
            return False
        print("  OK: Import button enabled")

        # Take screenshot before import
        page.locator('#sidebar').screenshot(path='/tmp/module_before_import.png')
        print("  Screenshot: /tmp/module_before_import.png")

        # Step 4: Click Import button
        print("[4/6] Clicking Import Module button...")
        import_btn.click()

        # Verify progress container appears (scoped to module tab)
        time.sleep(1)
        progress = page.locator('#module-tab .progress-container')
        if progress.count() > 0 and progress.evaluate('el => getComputedStyle(el).display') != 'none':
            print("  OK: Progress indicator visible")
            status = page.locator('#module-tab #progress-status')
            if status.count() > 0:
                print(f"  Status: {status.text_content()}")

        # Step 5: Wait for processing (up to 20 minutes)
        print("[5/6] Waiting for processing (up to 20 minutes)...")
        max_wait = 1200  # 20 minutes
        check_interval = 5
        elapsed = 0

        while elapsed < max_wait:
            # Check if result container is visible (scoped to module tab)
            result = page.locator('#module-tab .result-container')
            if result.count() > 0 and result.evaluate('el => getComputedStyle(el).display') != 'none':
                print(f"  Processing complete after {elapsed} seconds")
                break

            # Check for errors (notification toast or error in progress)
            error_notification = page.locator('.notification.error')
            if error_notification.count() > 0:
                error_text = error_notification.first.text_content()
                print(f"  ERROR notification: {error_text}")
                # Take screenshot of error
                page.locator('#sidebar').screenshot(path='/tmp/module_error.png')
                print("  Screenshot: /tmp/module_error.png")
                return False

            # Show progress (scoped to module tab)
            status = page.locator('#module-tab #progress-status')
            if status.count() > 0:
                current_status = status.text_content()
                if elapsed % 30 == 0:  # Print every 30 seconds
                    print(f"  [{elapsed}s] {current_status}")

            time.sleep(check_interval)
            elapsed += check_interval

        if elapsed >= max_wait:
            print(f"  TIMEOUT: Processing took longer than {max_wait} seconds")
            page.locator('#sidebar').screenshot(path='/tmp/module_timeout.png')
            return False

        # Step 6: Verify results
        print("[6/6] Verifying results...")

        result_container = page.locator('#module-tab .result-container')
        if result_container.count() == 0:
            print("  FAIL: Result container not found")
            return False

        # Check for result summary (scoped to module tab)
        result_summary = page.locator('#module-tab #result-summary')
        if result_summary.count() > 0:
            summary_html = result_summary.inner_html()
            print(f"  Result summary HTML length: {len(summary_html)} chars")

            # Check for "Import Complete" text
            if "Import Complete" in summary_html or "import complete" in summary_html.lower():
                print("  OK: 'Import Complete' message found")
            else:
                print("  WARNING: 'Import Complete' not found in summary")
                print(f"  Summary content: {result_summary.text_content()[:200]}")

        # Check for journal link (scoped to module tab)
        journal_link = page.locator('#module-tab .result-container .content-link[data-uuid*="JournalEntry"]')
        if journal_link.count() > 0:
            journal_uuid = journal_link.first.get_attribute('data-uuid')
            print(f"  OK: Journal created with UUID: {journal_uuid}")
        else:
            print("  WARNING: No journal link found in results")

        # Check for Import Another button
        import_another = page.locator('#import-another-btn')
        if import_another.count() > 0:
            print("  OK: 'Import Another Module' button visible")

        # Take final screenshot
        page.locator('#sidebar').screenshot(path='/tmp/module_result.png')
        print("  Screenshot: /tmp/module_result.png")

        print()
        print("=" * 60)
        print("END-TO-END TEST PASSED")
        print("=" * 60)
        return True


def main():
    parser = argparse.ArgumentParser(description='Module Upload E2E Test')
    parser.add_argument('--visible', action='store_true', help='Run with visible browser')
    args = parser.parse_args()

    success = run_e2e_test(headless=not args.visible)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
