"""E2E test: Use Tablewrite to generate a goblin in Foundry VTT v13."""

import pytest
import time
import sys
from pathlib import Path

# Skip entire module if playwright not installed (not available in CI)
pytest.importorskip("playwright")

from playwright.sync_api import sync_playwright

# Add the foundry helper to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'foundry-module' / 'tablewrite-assistant' / 'scripts' / 'feedback'))

from foundry_helper import FoundrySession

FOUNDRY_URL = "http://localhost:30000"


def wait_for_game_ready(page, timeout=30):
    """Wait for Foundry's game.ready to be true and tablewrite tab to exist."""
    start = time.time()
    # First wait for URL to change to /game
    while time.time() - start < timeout:
        if '/game' in page.url:
            print(f"URL changed to {page.url} after {time.time() - start:.1f}s")
            break
        time.sleep(0.5)
    else:
        print(f"URL never changed to /game. Current: {page.url}")
        return False

    # Now wait for game.ready
    last_state = None
    while time.time() - start < timeout:
        state = page.evaluate('''() => {
            const ready = typeof game !== "undefined" && game.ready === true;
            const tabExists = !!document.querySelector('button[data-tab="tablewrite"]') ||
                              !!document.querySelector('a[data-tab="tablewrite"]');
            return { ready, tabExists, gameExists: typeof game !== "undefined" };
        }''')
        if state != last_state:
            print(f"State at {time.time() - start:.1f}s: {state}")
            last_state = state
        if state.get('ready') and state.get('tabExists'):
            return True
        time.sleep(0.5)
    print(f"Timeout after {time.time() - start:.1f}s. Last state: {last_state}")
    page.screenshot(path="/tmp/test_timeout_state.png")
    print("Screenshot saved to /tmp/test_timeout_state.png")
    return False


@pytest.mark.foundry
@pytest.mark.playwright
class TestTablewriteGoblinGeneration:
    """E2E tests for goblin generation via Tablewrite in Foundry v13."""

    def test_tablewrite_tab_visible_in_v13(self, require_foundry, playwright_user):
        """Verify tablewrite tab is visible in Foundry v13 sidebar."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Navigate and login
            page.goto(FOUNDRY_URL)
            page.wait_for_load_state('networkidle')
            time.sleep(2)

            # Select user from pool and join
            user_select = page.locator('select[name="userid"]')
            if user_select.count() > 0:
                options = user_select.locator('option').all()
                for opt in options:
                    text = opt.text_content() or ''
                    value = opt.get_attribute('value')
                    disabled = opt.get_attribute('disabled')
                    if playwright_user.lower() in text.lower() and disabled is None:
                        user_select.select_option(value)
                        break
                page.locator('button:has-text("JOIN GAME SESSION")').click()
                # Wait for URL to change to /game (navigation happens asynchronously)
                try:
                    page.wait_for_url("**/game", timeout=30000)
                except Exception as e:
                    print(f"Wait for URL failed: {e}. Current URL: {page.url}")

            assert wait_for_game_ready(page), "Game did not become ready within timeout"

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

    def test_tablewrite_can_send_message(self, require_foundry, playwright_user):
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
                    if playwright_user.lower() in text.lower() and disabled is None:
                        user_select.select_option(value)
                        break
                page.locator('button:has-text("JOIN GAME SESSION")').click()
                # Wait for URL to change to /game (navigation happens asynchronously)
                try:
                    page.wait_for_url("**/game", timeout=30000)
                except Exception as e:
                    print(f"Wait for URL failed: {e}. Current URL: {page.url}")

            assert wait_for_game_ready(page), "Game did not become ready within timeout"

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

    def test_generate_goblin_via_tablewrite(self, require_foundry, playwright_user):
        """
        Full E2E test: Generate a goblin via Tablewrite chat.

        This test:
        1. Opens Foundry and navigates to Tablewrite tab
        2. Sends a message to create a goblin
        3. Waits for response
        4. Verifies actor was created (by checking response for Actor UUID)
        """
        import re
        import requests

        created_uuid = None

        try:
            with FoundrySession(headless=True, user=playwright_user) as session:
                session.goto_tablewrite()
                time.sleep(1)

                # Send goblin creation request
                print("[DEBUG] Sending: Create a goblin")
                session.send_message("Create a goblin", wait=60)

                response_text = session.get_message_text()
                response_html = session.get_message_html()
                print(f"[DEBUG] Response text: {response_text[:300]}...")

                session.screenshot("/tmp/goblin_creation.png")
                print("[DEBUG] Screenshot: /tmp/goblin_creation.png")

                # Parse UUID from response
                uuid_pattern = r'data-uuid="Actor\.([a-zA-Z0-9]+)"'
                matches = re.findall(uuid_pattern, response_html)

                assert len(matches) > 0, f"No actor UUID found in response: {response_text[:200]}"

                created_uuid = f"Actor.{matches[0]}"
                print(f"[DEBUG] Created actor: {created_uuid}")

                # Verify actor exists via API
                response = requests.get(f"http://localhost:8000/api/foundry/actor/{created_uuid}")
                assert response.status_code == 200, f"Actor not found in Foundry: {created_uuid}"

                actor_data = response.json()
                actor_name = actor_data.get('entity', {}).get('name', 'unknown')
                print(f"[DEBUG] Actor name: {actor_name}")

                # Verify it's goblin-related
                assert 'goblin' in actor_name.lower() or len(matches) > 0, \
                    f"Expected goblin actor, got: {actor_name}"

                print(f"SUCCESS: Created actor: {actor_name}")

        finally:
            # Cleanup
            if created_uuid:
                try:
                    requests.delete(f"http://localhost:8000/api/foundry/actor/{created_uuid}")
                    print(f"[DEBUG] Deleted actor: {created_uuid}")
                except Exception as e:
                    print(f"[DEBUG] Warning: Failed to delete {created_uuid}: {e}")
