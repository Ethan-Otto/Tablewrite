#!/usr/bin/env python3
"""
Module Tab UI Verification Script.

Verifies the Module Processing Tab UI renders correctly in FoundryVTT.

Usage:
    python test_module_tab.py

Prerequisites:
    1. Build the module: cd foundry-module/tablewrite-assistant && npm run build
    2. Foundry running at localhost:30000
    3. Tablewrite Assistant module enabled
    4. "Testing" user available (no password)

Verification Checks:
    1. Module tab button exists and is clickable
    2. Module tab content renders when clicked
    3. File drop zone exists
    4. All 4 checkboxes exist and are checked by default
    5. Import button exists and is initially disabled
"""

import sys
from pathlib import Path

# Add parent for foundry_helper import
sys.path.insert(0, str(Path(__file__).parent))

from foundry_helper import FoundrySession


class ModuleTabVerification:
    """Verify Module Tab UI elements."""

    def __init__(self, session: FoundrySession):
        self.session = session
        self.page = session.page
        self.results = {}

    def verify_all(self) -> dict:
        """Run all verification checks."""
        print("\n" + "=" * 60)
        print("MODULE TAB UI VERIFICATION")
        print("=" * 60)

        # Navigate to Tablewrite tab first
        print("\n[Setup] Navigating to Tablewrite tab...")
        self.session.goto_tablewrite()

        # Run all checks
        self.verify_module_tab_button()
        self.verify_module_tab_content()
        self.verify_file_drop_zone()
        self.verify_checkboxes()
        self.verify_import_button()

        # Summary
        self.print_summary()

        return self.results

    def verify_module_tab_button(self):
        """Check that the Module tab button exists and is clickable."""
        print("\n[1/5] Checking Module tab button...")

        # Look for the module tab button within tablewrite container
        module_btn = self.page.locator('.tablewrite-tabs .tab-btn[data-tab="module"]')

        if module_btn.count() == 0:
            self.results['module_tab_button'] = {
                'passed': False,
                'error': 'Module tab button not found'
            }
            print("  FAIL: Module tab button not found")
            return

        # Check if button is visible
        is_visible = module_btn.is_visible()
        if not is_visible:
            self.results['module_tab_button'] = {
                'passed': False,
                'error': 'Module tab button exists but not visible'
            }
            print("  FAIL: Module tab button not visible")
            return

        # Get button text
        button_text = module_btn.text_content()

        self.results['module_tab_button'] = {
            'passed': True,
            'text': button_text
        }
        print(f"  PASS: Module tab button found with text: '{button_text}'")

    def verify_module_tab_content(self):
        """Click Module tab and verify content container renders."""
        print("\n[2/5] Clicking Module tab and verifying content...")

        # Click the module tab button
        module_btn = self.page.locator('.tablewrite-tabs .tab-btn[data-tab="module"]')
        if module_btn.count() == 0:
            self.results['module_tab_content'] = {
                'passed': False,
                'error': 'Cannot click - Module tab button not found'
            }
            print("  FAIL: Module tab button not found")
            return

        module_btn.click()

        # Wait a moment for content to render
        self.page.wait_for_timeout(500)

        # Check module-tab container is now visible
        module_tab = self.page.locator('#module-tab')
        if module_tab.count() == 0:
            self.results['module_tab_content'] = {
                'passed': False,
                'error': '#module-tab container not found'
            }
            print("  FAIL: #module-tab container not found")
            return

        # Check display style - should NOT be 'none'
        display = module_tab.evaluate('el => window.getComputedStyle(el).display')
        if display == 'none':
            self.results['module_tab_content'] = {
                'passed': False,
                'error': f'#module-tab has display: none (not visible)'
            }
            print("  FAIL: #module-tab is hidden (display: none)")
            return

        # Check for the module-upload class inside
        module_upload = self.page.locator('#module-tab .module-upload')
        if module_upload.count() == 0:
            self.results['module_tab_content'] = {
                'passed': False,
                'error': '.module-upload container not found inside #module-tab'
            }
            print("  FAIL: .module-upload not found")
            return

        self.results['module_tab_content'] = {
            'passed': True,
            'display': display
        }
        print(f"  PASS: Module tab content visible (display: {display})")

    def verify_file_drop_zone(self):
        """Verify file drop zone exists."""
        print("\n[3/5] Checking file drop zone...")

        drop_zone = self.page.locator('#module-drop-zone')

        if drop_zone.count() == 0:
            self.results['file_drop_zone'] = {
                'passed': False,
                'error': '#module-drop-zone not found'
            }
            print("  FAIL: File drop zone not found")
            return

        # Check for inner text/instructions
        inner_text = drop_zone.text_content() or ""

        # Check for the file input inside
        file_input = self.page.locator('#module-file')
        has_file_input = file_input.count() > 0

        # Check file input accepts PDF
        accept_attr = ""
        if has_file_input:
            accept_attr = file_input.get_attribute('accept') or ""

        self.results['file_drop_zone'] = {
            'passed': True,
            'has_file_input': has_file_input,
            'accepts': accept_attr,
            'instructions': inner_text.strip()[:50] + "..." if len(inner_text) > 50 else inner_text.strip()
        }
        print(f"  PASS: Drop zone found")
        print(f"    - File input: {has_file_input}")
        print(f"    - Accepts: {accept_attr}")

    def verify_checkboxes(self):
        """Verify all 4 checkboxes exist and are checked by default."""
        print("\n[4/5] Checking processing option checkboxes...")

        checkbox_ids = [
            ('opt-journal', 'Extract Journal'),
            ('opt-actors', 'Extract Actors'),
            ('opt-maps', 'Extract Battle Maps'),
            ('opt-artwork', 'Generate Scene Artwork')
        ]

        checkbox_results = []
        all_found = True
        all_checked = True

        for checkbox_id, label in checkbox_ids:
            checkbox = self.page.locator(f'#module-tab #{checkbox_id}')

            if checkbox.count() == 0:
                checkbox_results.append({
                    'id': checkbox_id,
                    'label': label,
                    'found': False,
                    'checked': None
                })
                all_found = False
                print(f"  FAIL: Checkbox #{checkbox_id} ({label}) not found")
            else:
                is_checked = checkbox.is_checked()
                checkbox_results.append({
                    'id': checkbox_id,
                    'label': label,
                    'found': True,
                    'checked': is_checked
                })
                if not is_checked:
                    all_checked = False
                    print(f"  WARN: Checkbox #{checkbox_id} ({label}) is NOT checked")
                else:
                    print(f"  OK: #{checkbox_id} ({label}) - checked")

        passed = all_found and all_checked
        self.results['checkboxes'] = {
            'passed': passed,
            'all_found': all_found,
            'all_checked': all_checked,
            'details': checkbox_results
        }

        if passed:
            print(f"  PASS: All 4 checkboxes found and checked by default")
        elif all_found:
            print(f"  PARTIAL: All 4 checkboxes found but not all checked")
        else:
            print(f"  FAIL: Not all checkboxes found")

    def verify_import_button(self):
        """Verify Import button exists and is initially disabled."""
        print("\n[5/5] Checking Import button...")

        import_btn = self.page.locator('#module-tab #import-module-btn')

        if import_btn.count() == 0:
            self.results['import_button'] = {
                'passed': False,
                'error': '#import-module-btn not found'
            }
            print("  FAIL: Import button not found")
            return

        # Check if button is disabled
        is_disabled = import_btn.is_disabled()
        button_text = import_btn.text_content() or ""

        # Button should be disabled initially (no file selected)
        if not is_disabled:
            self.results['import_button'] = {
                'passed': False,
                'error': 'Import button should be disabled when no file selected',
                'text': button_text.strip()
            }
            print(f"  WARN: Import button is ENABLED (should be disabled initially)")
        else:
            self.results['import_button'] = {
                'passed': True,
                'disabled': is_disabled,
                'text': button_text.strip()
            }
            print(f"  PASS: Import button found, disabled={is_disabled}, text='{button_text.strip()}'")

    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)

        passed_count = sum(1 for r in self.results.values() if r.get('passed'))
        total_count = len(self.results)

        for check_name, result in self.results.items():
            status = "PASS" if result.get('passed') else "FAIL"
            print(f"  [{status}] {check_name}")

        print(f"\n  Total: {passed_count}/{total_count} checks passed")

        if passed_count == total_count:
            print("\n  *** ALL CHECKS PASSED ***")
        else:
            print("\n  *** SOME CHECKS FAILED ***")


def take_screenshot(session: FoundrySession, output_path: str = "/tmp/module_tab_ui.png"):
    """Take a screenshot of the current sidebar state."""
    print(f"\n[Screenshot] Saving to {output_path}...")
    session.screenshot(output_path)
    print(f"  Screenshot saved: {output_path}")


def main():
    """Main verification entry point."""
    print("=" * 60)
    print("MODULE TAB UI VERIFICATION SCRIPT")
    print("=" * 60)
    print("\nPrerequisites:")
    print("  1. Foundry running at localhost:30000")
    print("  2. Tablewrite Assistant module enabled")
    print("  3. Module built: npm run build")
    print("")

    # Optionally run in non-headless mode for debugging
    import argparse
    parser = argparse.ArgumentParser(description="Verify Module Tab UI")
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode')
    parser.add_argument('--screenshot', type=str, default='/tmp/module_tab_ui.png',
                        help='Path for screenshot output')
    args = parser.parse_args()

    headless = not args.visible

    try:
        with FoundrySession(headless=headless) as session:
            verifier = ModuleTabVerification(session)
            results = verifier.verify_all()

            # Take screenshot after verification
            take_screenshot(session, args.screenshot)

            # Return exit code based on results
            all_passed = all(r.get('passed') for r in results.values())
            return 0 if all_passed else 1

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
