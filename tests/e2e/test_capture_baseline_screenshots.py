"""
Captures baseline reference screenshots of the three main UI tabs.

Screenshots are written to tests/e2e/screenshots/baseline/ and committed as
reference images for human review. They are NOT used for pixel-diff
assertions (structural assertions in test_baseline_ui.py are the safety net).
"""

from pathlib import Path

SCREENSHOT_DIR = Path(__file__).resolve().parent / "screenshots" / "baseline"


def _goto(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")


def test_capture_default_tab(page, app_server):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    _goto(page, app_server)
    page.wait_for_function(
        "document.querySelector('#default-raw-textarea').value.length > 0",
        timeout=60000,
    )
    page.screenshot(path=str(SCREENSHOT_DIR / "tab-default.png"), full_page=True)


def test_capture_tailor_tab(page, app_server):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    _goto(page, app_server)
    page.click("#nav-tailor-btn")
    page.wait_for_selector("#generator-view:not(.hidden)", timeout=10000)
    page.screenshot(path=str(SCREENSHOT_DIR / "tab-tailor.png"), full_page=True)


def test_capture_chat_tab(page, app_server):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    _goto(page, app_server)
    page.click("#nav-chat-btn")
    page.wait_for_selector("#chatbot-view:not(.hidden)", timeout=10000)
    page.screenshot(path=str(SCREENSHOT_DIR / "tab-chat.png"), full_page=True)
