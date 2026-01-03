#!/usr/bin/env python3
"""
Foundry UI feedback helper for development.

Usage:
    from foundry_helper import FoundrySession

    with FoundrySession() as session:
        session.goto_tablewrite()
        session.send_message("/help")
        session.screenshot("/tmp/result.png")
        print(session.get_message_html())
"""

from playwright.sync_api import sync_playwright, Page
import time

FOUNDRY_URL = "http://localhost:30000"


class FoundrySession:
    def __init__(self, headless: bool = True, user: str = "Testing"):
        self.headless = headless
        self.user_filter = user
        self.playwright = None
        self.browser = None
        self.page: Page = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page(viewport={'width': 1920, 'height': 1080})
        self._login()
        return self

    def __exit__(self, *args):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def _login(self):
        """Log into Foundry as TestingGamemaster."""
        self.page.goto(FOUNDRY_URL)
        self.page.wait_for_load_state('networkidle')

        user_select = self.page.locator('select[name="userid"]')
        if user_select.count() > 0:
            options = user_select.locator('option').all()
            for opt in options:
                text = opt.text_content() or ""
                value = opt.get_attribute('value')
                disabled = opt.get_attribute('disabled')
                if self.user_filter in text and disabled is None:
                    user_select.select_option(value)
                    break
            self.page.locator('button:has-text("JOIN GAME SESSION")').click()
            self.page.wait_for_load_state('networkidle')
            time.sleep(3)

    def goto_tablewrite(self):
        """Click the Tablewrite tab."""
        tab = self.page.locator('a[data-tab="tablewrite"]')
        if tab.count() > 0:
            tab.click()
            time.sleep(1)
        return self

    def goto_chat(self):
        """Click the native Chat tab."""
        self.page.locator('a[data-tab="chat"]').click()
        time.sleep(0.5)
        return self

    def send_message(self, text: str, wait: float = 3.0):
        """Send a message in the Tablewrite chat."""
        textarea = self.page.locator('.tablewrite-input')
        if textarea.count() > 0:
            textarea.fill(text)
            textarea.press('Enter')
            time.sleep(wait)
        return self

    def screenshot(self, path: str = "/tmp/foundry_feedback.png", selector: str = "#sidebar"):
        """Take a screenshot of the sidebar (or custom selector)."""
        self.page.locator(selector).screenshot(path=path)
        print(f"Screenshot saved: {path}")
        return path

    def get_message_html(self) -> str:
        """Get the HTML of the latest assistant message."""
        msg = self.page.locator('.tablewrite-message--assistant').last
        if msg.count() > 0:
            return msg.inner_html()
        return ""

    def get_message_text(self) -> str:
        """Get the text content of the latest assistant message."""
        msg = self.page.locator('.tablewrite-message--assistant').last
        if msg.count() > 0:
            return msg.text_content()
        return ""

    def get_all_messages(self) -> list:
        """Get all messages as a list of dicts."""
        messages = []
        for msg in self.page.locator('.tablewrite-message').all():
            messages.append({
                'role': 'user' if 'user' in (msg.get_attribute('class') or '') else 'assistant',
                'html': msg.inner_html(),
                'text': msg.text_content()
            })
        return messages

    def get_element_styles(self, selector: str) -> dict:
        """Get computed styles for an element."""
        el = self.page.locator(selector)
        if el.count() > 0:
            return el.evaluate('''el => {
                const s = window.getComputedStyle(el);
                return {
                    height: s.height,
                    width: s.width,
                    padding: s.padding,
                    margin: s.margin,
                    color: s.color,
                    background: s.background,
                    display: s.display
                };
            }''')
        return {}

    def check_tab_switching(self) -> dict:
        """Verify tab switching works correctly."""
        results = {}

        # Go to tablewrite
        self.goto_tablewrite()
        tw_section = self.page.locator('#tablewrite')
        results['tablewrite_visible'] = tw_section.evaluate('el => window.getComputedStyle(el).display') != 'none'

        # Go to chat
        self.goto_chat()
        chat_section = self.page.locator('#chat')
        results['chat_visible'] = chat_section.evaluate('el => window.getComputedStyle(el).display') != 'none'
        results['tablewrite_hidden'] = self.page.locator('#tablewrite').evaluate('el => window.getComputedStyle(el).display') == 'none'

        return results


# Quick feedback functions for one-liners
def quick_screenshot(path: str = "/tmp/foundry_feedback.png"):
    """Take a quick screenshot of the Tablewrite tab."""
    with FoundrySession() as s:
        s.goto_tablewrite()
        return s.screenshot(path)


def test_message(text: str = "/help"):
    """Send a message and return the response."""
    with FoundrySession() as s:
        s.goto_tablewrite()
        s.send_message(text)
        return {
            'html': s.get_message_html(),
            'text': s.get_message_text()
        }


if __name__ == "__main__":
    # Demo usage
    print("Taking feedback screenshot...")
    with FoundrySession() as session:
        session.goto_tablewrite()
        session.send_message("/help")
        session.screenshot("/tmp/feedback_demo.png")
        print(f"Messages: {len(session.get_all_messages())}")
        print(f"Response preview: {session.get_message_text()[:100]}...")
