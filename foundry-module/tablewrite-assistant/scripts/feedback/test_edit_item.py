#!/usr/bin/env python3
"""
Test editing existing items on an actor via the Tablewrite assistant.

Usage:
    python test_edit_item.py --visible
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

        # Test: Edit item on an actor using @mention
        print("\n[Test 1] Edit weapon attack bonus to 0...")

        # First check if Hobgoblin Iron Shadow exists
        textarea = session.page.locator('.tablewrite-input')
        textarea.fill("")
        textarea.focus()
        time.sleep(0.2)

        # Type @Hob to trigger mention autocomplete
        textarea.type("@Hob")
        time.sleep(1)

        # Check if dropdown appeared
        dropdown = session.page.locator('.mention-dropdown')
        if dropdown.count() > 0 and dropdown.is_visible():
            print("  Dropdown visible - selecting Iron Shadow")

            # Press Tab to select
            textarea.press("Tab")
            time.sleep(0.5)

            # Now add the edit request
            textarea.type(" Set the Longbow attack bonus to 0")
            time.sleep(0.3)

            # Submit by pressing Enter
            textarea.press("Enter")

            # Wait for response (polling for completion)
            for i in range(60):
                time.sleep(1)
                thinking = session.page.locator('.tablewrite-thinking')
                if thinking.count() == 0 or not thinking.is_visible():
                    break
                if i % 10 == 0:
                    print(f"    Still thinking... ({i}s)")

            time.sleep(1)  # Brief pause after response

            # Get response
            response = session.get_message_text()
            print(f"  Response: {response[:500] if response else 'empty'}...")

            if "edited" in response.lower() or "updated" in response.lower():
                print("  PASS: Item edit appears to have been processed")
            else:
                print("  RESULT: Response received, check if edit worked")
        else:
            print("  Skipping test - Hobgoblin Iron Shadow actor not found")
            print("  Create this actor first to run the test")

        session.screenshot("/tmp/test_edit_item.png")
        print("\n[Screenshot] /tmp/test_edit_item.png")

        return 0


if __name__ == "__main__":
    sys.exit(main())
