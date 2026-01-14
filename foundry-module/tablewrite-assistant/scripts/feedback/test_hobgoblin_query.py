#!/usr/bin/env python3
"""
Quick test for Hobgoblin Iron Shadow attack breakdown.

Usage:
    python test_hobgoblin_query.py --visible
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

        # Find Hobgoblin Iron Shadow
        actors = session.page.evaluate('''() => {
            if (!game.actors) return [];
            return game.actors.map(a => ({
                name: a.name,
                uuid: a.uuid
            })).filter(a => a.name.toLowerCase().includes('hobgoblin'));
        }''')

        if not actors:
            print("No hobgoblin actors found, using first available")
            actors = session.page.evaluate('''() => {
                if (!game.actors) return [];
                return game.actors.contents.slice(0, 1).map(a => ({
                    name: a.name,
                    uuid: a.uuid
                }));
            }''')

        if not actors:
            print("No actors found!")
            return 1

        actor = actors[0]
        print(f"\n[Test] Using: {actor['name']} ({actor['uuid']})")

        textarea = session.page.locator('.tablewrite-input')

        # Query specifically about attack breakdown
        query = f"@[{actor['name']}]({actor['uuid']}) Why is the longbow +14? Break down the exact calculation."
        print(f"\n[Query] {query}")

        textarea.fill(query)
        time.sleep(0.3)
        textarea.press("Enter")

        print("\n[Waiting] 20 seconds for AI response...")
        time.sleep(20)

        response = session.get_message_text()
        print(f"\n[Response]\n{response}")

        # Check for correct proficiency
        if "+2" in response and "prof" in response.lower():
            print("\n*** SUCCESS: Response mentions +2 proficiency ***")
        elif "+6" in response or "+7" in response:
            print("\n*** FAIL: Response has incorrect proficiency (+6 or +7) ***")
        else:
            print("\n*** MANUAL CHECK: Verify proficiency in response ***")

        session.screenshot("/tmp/hobgoblin_test.png")
        print("\n[Screenshot] /tmp/hobgoblin_test.png")

        return 0


if __name__ == "__main__":
    sys.exit(main())
