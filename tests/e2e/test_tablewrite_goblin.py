"""E2E test: Use Tablewrite to generate a goblin in Foundry VTT v13."""

import pytest
import time
import sys
from pathlib import Path

# Add the foundry helper to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'foundry-module' / 'tablewrite-assistant' / 'scripts' / 'feedback'))

from playwright.sync_api import sync_playwright


FOUNDRY_URL = "http://localhost:30000"


@pytest.mark.integration
@pytest.mark.playwright
@pytest.mark.requires_foundry
class TestTablewriteGoblinGeneration:
    """E2E tests for goblin generation via Tablewrite in Foundry v13."""

    def test_tablewrite_tab_visible_in_v13(self, require_foundry):
        """Verify tablewrite tab is visible in Foundry v13 sidebar."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Navigate and login
            page.goto(FOUNDRY_URL)
            page.wait_for_load_state('networkidle')
            time.sleep(2)

            # Select Testing user and join
            user_select = page.locator('select[name="userid"]')
            if user_select.count() > 0:
                options = user_select.locator('option').all()
                for opt in options:
                    text = opt.text_content() or ''
                    value = opt.get_attribute('value')
                    disabled = opt.get_attribute('disabled')
                    if 'testing' in text.lower() and disabled is None:
                        user_select.select_option(value)
                        break
                page.locator('button:has-text("JOIN GAME SESSION")').click()
                page.wait_for_load_state('networkidle')
                time.sleep(5)

            # Verify module is loaded and active
            module_info = page.evaluate('''() => {
                if (typeof game === 'undefined' || !game.modules) return null;
                const mod = game.modules.get('tablewrite-assistant');
                if (!mod) return { error: 'Module not found' };
                return { id: mod.id, active: mod.active, compatibility: mod.compatibility };
            }''')

            assert module_info is not None, "game.modules not available"
            assert 'error' not in module_info, f"Module error: {module_info.get('error')}"
            assert module_info['active'], "Tablewrite module is not active"

            # Verify v13 compatibility
            compat = module_info.get('compatibility', {})
            assert compat.get('verified') == '13', f"Module not verified for v13: {compat}"

            # Verify tablewrite tab exists
            tw_tab = page.locator('button[data-tab="tablewrite"]')
            assert tw_tab.count() > 0, "Tablewrite tab button not found in sidebar"

            # Click the tab and verify content container exists
            tw_tab.click()
            time.sleep(1)

            tw_content = page.locator('#tablewrite')
            assert tw_content.count() > 0, "Tablewrite content container not found"

            browser.close()

    def test_tablewrite_can_send_message(self, require_foundry):
        """Verify we can click tablewrite tab and it initializes."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Navigate and login
            page.goto(FOUNDRY_URL)
            page.wait_for_load_state('networkidle')
            time.sleep(2)

            user_select = page.locator('select[name="userid"]')
            if user_select.count() > 0:
                options = user_select.locator('option').all()
                for opt in options:
                    text = opt.text_content() or ''
                    value = opt.get_attribute('value')
                    disabled = opt.get_attribute('disabled')
                    if 'testing' in text.lower() and disabled is None:
                        user_select.select_option(value)
                        break
                page.locator('button:has-text("JOIN GAME SESSION")').click()
                page.wait_for_load_state('networkidle')
                time.sleep(5)

            # Click tablewrite tab
            tw_tab = page.locator('button[data-tab="tablewrite"]')
            assert tw_tab.count() > 0, "Tablewrite tab not found"
            tw_tab.click()
            time.sleep(2)  # Wait for initialization

            # Check that the tab content is initialized
            tw_content = page.locator('#tablewrite')
            assert tw_content.count() > 0, "Tablewrite content not found"

            # Check for initialized attribute
            is_initialized = tw_content.get_attribute('data-initialized')
            assert is_initialized == 'true', f"Tablewrite not initialized: {is_initialized}"

            # Check for input field
            input_field = page.locator('.tablewrite-input')
            assert input_field.count() > 0, "Tablewrite input field not found"

            browser.close()

    def test_generate_goblin_via_tablewrite(self, require_foundry):
        """
        Full E2E test: Generate a goblin via Tablewrite chat.

        This test:
        1. Opens Foundry and navigates to Tablewrite tab
        2. Sends a message to create a goblin
        3. Waits for response
        4. Verifies actor was created in Foundry
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Capture console for debugging
            console_msgs = []
            page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

            # Navigate and login
            page.goto(FOUNDRY_URL)
            page.wait_for_load_state('networkidle')
            time.sleep(2)

            user_select = page.locator('select[name="userid"]')
            if user_select.count() > 0:
                options = user_select.locator('option').all()
                for opt in options:
                    text = opt.text_content() or ''
                    value = opt.get_attribute('value')
                    disabled = opt.get_attribute('disabled')
                    if 'testing' in text.lower() and disabled is None:
                        user_select.select_option(value)
                        break
                page.locator('button:has-text("JOIN GAME SESSION")').click()
                page.wait_for_load_state('networkidle')
                time.sleep(5)

            # Get initial actor count
            initial_actors = page.evaluate('''() => {
                if (typeof game === 'undefined' || !game.actors) return [];
                return game.actors.map(a => ({ name: a.name, uuid: a.uuid }));
            }''')
            initial_count = len(initial_actors)

            # Click tablewrite tab
            tw_tab = page.locator('button[data-tab="tablewrite"]')
            assert tw_tab.count() > 0, "Tablewrite tab not found"
            tw_tab.click()
            time.sleep(2)

            # Find and use input field
            input_field = page.locator('.tablewrite-input')
            assert input_field.count() > 0, "Tablewrite input not found"

            # Send goblin creation request
            input_field.fill("Create a goblin")
            input_field.press('Enter')

            # Wait for response (up to 60 seconds for AI generation)
            max_wait = 60
            start = time.time()
            response_found = False

            while time.time() - start < max_wait:
                # Check for assistant message
                assistant_msgs = page.locator('.tablewrite-message--assistant')
                if assistant_msgs.count() > 0:
                    response_found = True
                    break
                time.sleep(2)

            assert response_found, "No response received from Tablewrite within timeout"

            # Wait a bit more for actor creation
            time.sleep(5)

            # Check if actor was created
            final_actors = page.evaluate('''() => {
                if (typeof game === 'undefined' || !game.actors) return [];
                return game.actors.map(a => ({ name: a.name, uuid: a.uuid }));
            }''')

            # Debug: print console messages on failure
            if len(final_actors) <= initial_count:
                print("Console messages:")
                for msg in console_msgs:
                    if 'tablewrite' in msg.lower() or 'actor' in msg.lower():
                        print(f"  {msg}")

            # Verify new actor was created
            new_actors = [a for a in final_actors if a not in initial_actors]
            assert len(new_actors) > 0, f"No new actor created. Had {initial_count}, now have {len(final_actors)}"

            # Verify it's a goblin-ish actor (name contains goblin)
            goblin_actors = [a for a in new_actors if 'goblin' in a['name'].lower()]
            assert len(goblin_actors) > 0, f"No goblin actor found. New actors: {new_actors}"

            print(f"SUCCESS: Created goblin actor: {goblin_actors[0]}")

            browser.close()
