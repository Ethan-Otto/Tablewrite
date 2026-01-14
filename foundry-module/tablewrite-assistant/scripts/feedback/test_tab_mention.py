#!/usr/bin/env python3
"""
Test Tab behavior when selecting @mentions.

Usage:
    python test_tab_mention.py --visible
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from foundry_helper import FoundrySession


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--visible', action='store_true')
    args = parser.parse_args()

    with FoundrySession(headless=not args.visible) as session:
        print("\n[Setup] Navigating to Tablewrite...")
        session.goto_tablewrite()
        time.sleep(1)

        textarea = session.page.locator('.tablewrite-input')

        # Test 1: Tab with mention autocomplete open
        print("\n[Test 1] Tab with mention autocomplete open...")

        # Type @ to trigger autocomplete
        textarea.fill("")
        textarea.focus()
        time.sleep(0.2)

        textarea.type("@Hob")
        time.sleep(1)  # Wait for autocomplete

        # Check if dropdown appeared
        dropdown = session.page.locator('.mention-dropdown')
        if dropdown.count() > 0 and dropdown.is_visible():
            print("  Dropdown visible")

            # Press Tab to select
            textarea.press("Tab")
            time.sleep(0.5)

            # Check if focus is still in textarea
            focused_tag = session.page.evaluate('() => document.activeElement?.tagName')
            focused_class = session.page.evaluate('() => document.activeElement?.className')
            print(f"  After Tab - focused: {focused_tag} ({focused_class})")

            # Check if mention was inserted
            input_value = textarea.input_value()
            print(f"  Input value: {input_value[:50]}...")

            if focused_tag == 'TEXTAREA' and '@[' in input_value:
                print("  PASS: Tab selected mention and kept focus")
            else:
                print("  FAIL: Tab moved focus or didn't insert mention")
        else:
            print("  No dropdown appeared - check if actors exist")

        # Test 2: Tab without autocomplete (should stay in input)
        print("\n[Test 2] Tab without autocomplete...")

        textarea.fill("Hello world")
        textarea.focus()
        time.sleep(0.2)

        textarea.press("Tab")
        time.sleep(0.3)

        focused_tag = session.page.evaluate('() => document.activeElement?.tagName')
        print(f"  After Tab - focused: {focused_tag}")

        if focused_tag == 'TEXTAREA':
            print("  PASS: Tab kept focus in textarea")
        else:
            print("  FAIL: Tab moved focus away")

        session.screenshot("/tmp/tab_mention_test.png")
        print("\n[Screenshot] /tmp/tab_mention_test.png")

        return 0


if __name__ == "__main__":
    sys.exit(main())
