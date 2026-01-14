#!/usr/bin/env python3
"""
Actor Query with @Mentions E2E Test.

Tests that @mentioning an actor and asking about its abilities/attacks
correctly fetches and returns the actor's data.

Usage:
    python test_actor_query_mentions.py
    python test_actor_query_mentions.py --visible  # Run in visible mode for debugging

Prerequisites:
    1. Foundry running at localhost:30000
    2. Backend running at localhost:8000
    3. Tablewrite Assistant module enabled and connected
    4. At least one actor exists in the world (creates test actor if needed)
"""

import sys
import time
from pathlib import Path

# Add parent for foundry_helper import
sys.path.insert(0, str(Path(__file__).parent))

from foundry_helper import FoundrySession


class ActorQueryMentionTest:
    """Test actor query with @mentions."""

    def __init__(self, session: FoundrySession):
        self.session = session
        self.page = session.page
        self.results = {}
        self.test_actor_name = None
        self.test_actor_uuid = None

    def run_all_tests(self) -> dict:
        """Run all tests."""
        print("\n" + "=" * 60)
        print("ACTOR QUERY WITH @MENTIONS E2E TEST")
        print("=" * 60)

        # Setup
        print("\n[Setup] Navigating to Tablewrite tab...")
        self.session.goto_tablewrite()
        time.sleep(1)

        # Find or create test actor
        self.setup_test_actor()

        if not self.test_actor_uuid:
            print("\nFAIL: No test actor available")
            return self.results

        # Run tests
        self.test_mention_autocomplete()
        self.test_actor_query_combat()
        self.test_actor_query_abilities()

        # Summary
        self.print_summary()

        return self.results

    def setup_test_actor(self):
        """Find an existing actor or create one for testing."""
        print("\n[Setup] Finding test actor...")

        # Get list of actors via JS
        actors = self.page.evaluate('''() => {
            if (!game.actors) return [];
            return game.actors.map(a => ({
                name: a.name,
                uuid: a.uuid,
                id: a.id
            }));
        }''')

        if actors and len(actors) > 0:
            # Use first available actor
            self.test_actor_name = actors[0]['name']
            self.test_actor_uuid = actors[0]['uuid']
            print(f"  Using existing actor: {self.test_actor_name} ({self.test_actor_uuid})")
        else:
            print("  No actors found, creating test actor...")
            # Create a simple test actor
            result = self.page.evaluate('''async () => {
                const actor = await Actor.create({
                    name: "Test Goblin",
                    type: "npc",
                    system: {
                        abilities: {
                            str: { value: 8 },
                            dex: { value: 14 },
                            con: { value: 10 },
                            int: { value: 10 },
                            wis: { value: 8 },
                            cha: { value: 8 }
                        },
                        attributes: {
                            ac: { value: 15 },
                            hp: { value: 7, max: 7 }
                        },
                        details: {
                            cr: 0.25
                        }
                    }
                });
                if (actor) {
                    return { name: actor.name, uuid: actor.uuid, id: actor.id };
                }
                return null;
            }''')
            if result:
                self.test_actor_name = result['name']
                self.test_actor_uuid = result['uuid']
                print(f"  Created test actor: {self.test_actor_name} ({self.test_actor_uuid})")
            else:
                print("  FAIL: Could not create test actor")

    def test_mention_autocomplete(self):
        """Test that @mention autocomplete works."""
        print("\n[1/3] Testing @mention autocomplete...")

        # Clear input and type @
        textarea = self.page.locator('.tablewrite-input')
        textarea.fill("")
        time.sleep(0.3)

        # Type @ followed by first few chars of actor name
        search_text = self.test_actor_name[:3] if self.test_actor_name else "Gob"
        textarea.type(f"@{search_text}")
        time.sleep(1)  # Wait for autocomplete

        # Check if dropdown appeared
        dropdown = self.page.locator('.mention-dropdown')
        dropdown_visible = dropdown.count() > 0 and dropdown.is_visible()

        if not dropdown_visible:
            self.results['mention_autocomplete'] = {
                'passed': False,
                'error': 'Mention dropdown did not appear'
            }
            print("  FAIL: Mention dropdown did not appear")
            # Clear for next test
            textarea.fill("")
            return

        # Check if our actor is in the dropdown
        actor_item = self.page.locator(f'.mention-item:has-text("{self.test_actor_name}")')
        actor_found = actor_item.count() > 0

        if not actor_found:
            self.results['mention_autocomplete'] = {
                'passed': False,
                'error': f'Actor "{self.test_actor_name}" not found in dropdown'
            }
            print(f"  FAIL: Actor not found in dropdown")
            textarea.fill("")
            return

        # Select the actor with Tab
        textarea.press("Tab")
        time.sleep(0.5)

        # Check that mention was inserted
        input_value = textarea.input_value()
        mention_format = f"@[{self.test_actor_name}]"

        if mention_format not in input_value:
            self.results['mention_autocomplete'] = {
                'passed': False,
                'error': f'Mention not inserted correctly. Got: {input_value}'
            }
            print(f"  FAIL: Mention not inserted. Got: {input_value}")
            textarea.fill("")
            return

        self.results['mention_autocomplete'] = {
            'passed': True,
            'input_value': input_value
        }
        print(f"  PASS: Mention autocomplete works")
        print(f"    Input value: {input_value[:60]}...")

        # Don't clear - keep the mention for next test
        # Store the current input for the query test
        self.mention_input = input_value

    def test_actor_query_combat(self):
        """Test querying actor's combat info."""
        print("\n[2/3] Testing actor query (combat)...")

        textarea = self.page.locator('.tablewrite-input')

        # Build query with mention
        if hasattr(self, 'mention_input') and self.mention_input:
            # Use existing mention
            query = f"{self.mention_input} What attacks does this creature have?"
        else:
            # Create fresh mention
            query = f"@[{self.test_actor_name}]({self.test_actor_uuid}) What attacks does this creature have?"

        textarea.fill(query)
        time.sleep(0.3)

        # Send the message
        textarea.press("Enter")

        # Wait for response (longer timeout for AI)
        print("  Waiting for AI response...")
        time.sleep(15)

        # Get the response
        response_text = self.session.get_message_text()

        if not response_text:
            self.results['actor_query_combat'] = {
                'passed': False,
                'error': 'No response received'
            }
            print("  FAIL: No response received")
            return

        # Check for error indicators
        has_error = "error" in response_text.lower() or "not found" in response_text.lower()
        has_actor_name = self.test_actor_name.lower() in response_text.lower()

        # Check for combat-related content (weapons, attacks, damage, etc.)
        combat_keywords = ['attack', 'damage', 'weapon', 'hit', 'combat', 'action']
        has_combat_info = any(kw in response_text.lower() for kw in combat_keywords)

        if has_error and "Actor not found" in response_text:
            self.results['actor_query_combat'] = {
                'passed': False,
                'error': 'Actor not found error - UUID issue',
                'response': response_text[:200]
            }
            print(f"  FAIL: Actor not found error")
            print(f"    Response: {response_text[:200]}...")
            return

        if not has_combat_info and not has_actor_name:
            self.results['actor_query_combat'] = {
                'passed': False,
                'error': 'Response does not contain combat info',
                'response': response_text[:200]
            }
            print(f"  FAIL: No combat info in response")
            print(f"    Response: {response_text[:200]}...")
            return

        self.results['actor_query_combat'] = {
            'passed': True,
            'has_actor_name': has_actor_name,
            'has_combat_info': has_combat_info,
            'response_preview': response_text[:200]
        }
        print(f"  PASS: Combat query returned valid response")
        print(f"    Has actor name: {has_actor_name}")
        print(f"    Has combat info: {has_combat_info}")
        print(f"    Response: {response_text[:100]}...")

    def test_actor_query_abilities(self):
        """Test querying actor's ability scores."""
        print("\n[3/3] Testing actor query (abilities)...")

        textarea = self.page.locator('.tablewrite-input')

        # Create query with mention
        query = f"@[{self.test_actor_name}]({self.test_actor_uuid}) What are its ability scores?"
        textarea.fill(query)
        time.sleep(0.3)

        # Send the message
        textarea.press("Enter")

        # Wait for response
        print("  Waiting for AI response...")
        time.sleep(15)

        # Get the response
        response_text = self.session.get_message_text()

        if not response_text:
            self.results['actor_query_abilities'] = {
                'passed': False,
                'error': 'No response received'
            }
            print("  FAIL: No response received")
            return

        # Check for ability-related content
        ability_keywords = ['str', 'dex', 'con', 'int', 'wis', 'cha', 'strength', 'dexterity',
                          'constitution', 'intelligence', 'wisdom', 'charisma', 'ability', 'modifier']
        has_ability_info = any(kw in response_text.lower() for kw in ability_keywords)

        has_error = "error" in response_text.lower() or "not found" in response_text.lower()

        if has_error and "Actor not found" in response_text:
            self.results['actor_query_abilities'] = {
                'passed': False,
                'error': 'Actor not found error - UUID issue',
                'response': response_text[:200]
            }
            print(f"  FAIL: Actor not found error")
            return

        if not has_ability_info:
            self.results['actor_query_abilities'] = {
                'passed': False,
                'error': 'Response does not contain ability info',
                'response': response_text[:200]
            }
            print(f"  FAIL: No ability info in response")
            print(f"    Response: {response_text[:200]}...")
            return

        self.results['actor_query_abilities'] = {
            'passed': True,
            'has_ability_info': has_ability_info,
            'response_preview': response_text[:200]
        }
        print(f"  PASS: Abilities query returned valid response")
        print(f"    Response: {response_text[:100]}...")

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
    print("ACTOR QUERY WITH @MENTIONS E2E TEST")
    print("=" * 60)
    print("\nPrerequisites:")
    print("  1. Foundry running at localhost:30000")
    print("  2. Backend running at localhost:8000")
    print("  3. Tablewrite module enabled and connected")
    print("")

    import argparse
    parser = argparse.ArgumentParser(description="Test actor query with @mentions")
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode')
    parser.add_argument('--screenshot', type=str, default='/tmp/actor_query_test.png',
                        help='Path for screenshot output')
    args = parser.parse_args()

    headless = not args.visible

    try:
        with FoundrySession(headless=headless) as session:
            tester = ActorQueryMentionTest(session)
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
