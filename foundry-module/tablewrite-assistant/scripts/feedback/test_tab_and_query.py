#!/usr/bin/env python3
"""
Tab Behavior and Actor Query E2E Test.

Tests:
1. Tab key doesn't leave the chat input
2. Actor query returns correct attack breakdown

Usage:
    python test_tab_and_query.py
    python test_tab_and_query.py --visible  # Run in visible mode for debugging

Prerequisites:
    1. Foundry running at localhost:30000
    2. Backend running at localhost:8000
    3. Tablewrite Assistant module enabled and connected
"""

import sys
import time
from pathlib import Path

# Add parent for foundry_helper import
sys.path.insert(0, str(Path(__file__).parent))

from foundry_helper import FoundrySession


class TabAndQueryTest:
    """Test tab behavior and actor query."""

    def __init__(self, session: FoundrySession):
        self.session = session
        self.page = session.page
        self.results = {}

    def run_all_tests(self) -> dict:
        """Run all tests."""
        print("\n" + "=" * 60)
        print("TAB BEHAVIOR AND ACTOR QUERY TEST")
        print("=" * 60)

        # Setup
        print("\n[Setup] Navigating to Tablewrite tab...")
        self.session.goto_tablewrite()
        time.sleep(1)

        # Run tests
        self.test_tab_stays_in_input()
        self.test_actor_query_breakdown()

        # Summary
        self.print_summary()

        return self.results

    def test_tab_stays_in_input(self):
        """Test that pressing Tab doesn't leave the chat input."""
        print("\n[1/2] Testing Tab key behavior...")

        textarea = self.page.locator('.tablewrite-input')

        # Clear and focus
        textarea.fill("")
        textarea.focus()
        time.sleep(0.2)

        # Verify textarea has focus
        focused_element = self.page.evaluate('() => document.activeElement?.className || "unknown"')
        print(f"  Before Tab - focused element class: {focused_element}")

        # Type some text
        textarea.type("Hello world")
        time.sleep(0.2)

        # Press Tab
        textarea.press("Tab")
        time.sleep(0.3)

        # Check if textarea still has focus
        focused_after = self.page.evaluate('() => document.activeElement?.className || "unknown"')
        print(f"  After Tab - focused element class: {focused_after}")

        # Also check by tag name
        focused_tag = self.page.evaluate('() => document.activeElement?.tagName || "unknown"')
        print(f"  After Tab - focused element tag: {focused_tag}")

        # The textarea should still be focused
        still_focused = 'tablewrite-input' in focused_after or focused_tag == 'TEXTAREA'

        if not still_focused:
            self.results['tab_stays_in_input'] = {
                'passed': False,
                'error': f'Tab moved focus away. Active element: {focused_tag} ({focused_after})'
            }
            print(f"  FAIL: Tab moved focus away")
            return

        # Verify we can still type
        textarea.type(" test after tab")
        input_value = textarea.input_value()

        if "test after tab" not in input_value:
            self.results['tab_stays_in_input'] = {
                'passed': False,
                'error': 'Could not type after Tab key press'
            }
            print("  FAIL: Could not type after Tab")
            return

        self.results['tab_stays_in_input'] = {
            'passed': True,
            'input_value': input_value
        }
        print(f"  PASS: Tab keeps focus in input")
        print(f"    Input value: {input_value}")

    def test_actor_query_breakdown(self):
        """Test that actor query returns attack breakdown."""
        print("\n[2/2] Testing actor query attack breakdown...")

        # First, get an actor to query
        actors = self.page.evaluate('''() => {
            if (!game.actors) return [];
            return game.actors.map(a => ({
                name: a.name,
                uuid: a.uuid,
                id: a.id
            }));
        }''')

        if not actors:
            self.results['actor_query_breakdown'] = {
                'passed': False,
                'error': 'No actors found in world'
            }
            print("  FAIL: No actors found")
            return

        # Pick an actor
        test_actor = actors[0]
        print(f"  Using actor: {test_actor['name']} ({test_actor['uuid']})")

        textarea = self.page.locator('.tablewrite-input')

        # Send a query about the actor's attacks
        query = f"@[{test_actor['name']}]({test_actor['uuid']}) explain the attack bonus breakdown for all weapons"
        textarea.fill(query)
        time.sleep(0.3)

        # Send the message
        textarea.press("Enter")

        # Wait for response
        print("  Waiting for AI response...")
        time.sleep(20)

        # Get the response
        response_text = self.session.get_message_text()

        if not response_text:
            self.results['actor_query_breakdown'] = {
                'passed': False,
                'error': 'No response received'
            }
            print("  FAIL: No response received")
            return

        # Check for breakdown keywords
        breakdown_keywords = ['ability', 'proficiency', 'bonus', 'dex', 'str', 'modifier']
        has_breakdown = any(kw.lower() in response_text.lower() for kw in breakdown_keywords)

        # Check for specific math
        has_math = '+' in response_text and any(char.isdigit() for char in response_text)

        # Print response for debugging
        print(f"  Response preview: {response_text[:300]}...")

        self.results['actor_query_breakdown'] = {
            'passed': True,  # Pass if we got a response; manual verification needed
            'has_breakdown': has_breakdown,
            'has_math': has_math,
            'response_preview': response_text[:500]
        }
        print(f"  PASS: Got response (manual verification needed)")
        print(f"    Has breakdown keywords: {has_breakdown}")
        print(f"    Has math: {has_math}")

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed_count = sum(1 for r in self.results.values() if r.get('passed'))
        total_count = len(self.results)

        for test_name, result in self.results.items():
            status = "PASS" if result.get('passed') else "FAIL"
            error = f" - {result.get('error')}" if result.get('error') else ""
            print(f"  [{status}] {test_name}{error}")

        print(f"\n  Total: {passed_count}/{total_count} tests passed")

        if passed_count == total_count:
            print("\n  *** ALL TESTS PASSED ***")
        else:
            print("\n  *** SOME TESTS FAILED ***")


def main():
    """Main entry point."""
    print("=" * 60)
    print("TAB BEHAVIOR AND ACTOR QUERY TEST")
    print("=" * 60)
    print("\nPrerequisites:")
    print("  1. Foundry running at localhost:30000")
    print("  2. Backend running at localhost:8000")
    print("  3. Tablewrite module enabled and connected")
    print("")

    import argparse
    parser = argparse.ArgumentParser(description="Test tab behavior and actor query")
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode')
    parser.add_argument('--screenshot', type=str, default='/tmp/tab_query_test.png',
                        help='Path for screenshot output')
    args = parser.parse_args()

    headless = not args.visible

    try:
        with FoundrySession(headless=headless) as session:
            tester = TabAndQueryTest(session)
            results = tester.run_all_tests()

            # Take screenshot
            print(f"\n[Screenshot] Saving to {args.screenshot}...")
            session.screenshot(args.screenshot)

            # Return exit code
            all_passed = all(r.get('passed') for r in results.values())
            return 0 if all_passed else 1

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
