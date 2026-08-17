"""
Baseline characterization tests for the browser UI of the local server.

Uses Playwright (via pytest-playwright). Navigates with
`wait_until="domcontentloaded"` so tests never hang on external Google Fonts.
"""

import re

from playwright.sync_api import expect

PAGE_TITLE = "Prasad Resumes — GraphRAG Knowledge Graph & Tailored Career Engine"
HIDDEN_RE = re.compile("hidden")


def _goto(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")


def test_page_loads_with_title(page, app_server):
    _goto(page, app_server)
    assert page.title() == PAGE_TITLE


def test_default_tab_active_and_resume_loads(page, app_server):
    _goto(page, app_server)
    default_btn = page.locator("#nav-default-btn")
    expect(default_btn).to_have_attribute("aria-selected", "true", timeout=10000)
    # The default view fetches /api/default-resume and fills the textarea.
    page.wait_for_function(
        "document.querySelector('#default-raw-textarea').value.length > 0",
        timeout=60000,
    )
    textarea_value = page.locator("#default-raw-textarea").input_value()
    assert len(textarea_value) > 0
    assert not textarea_value.startswith("Error loading default resume")


def test_tab_switching(page, app_server):
    _goto(page, app_server)

    page.click("#nav-tailor-btn")
    expect(page.locator("#generator-view")).not_to_have_class(HIDDEN_RE, timeout=10000)

    page.click("#nav-chat-btn")
    expect(page.locator("#chatbot-view")).not_to_have_class(HIDDEN_RE, timeout=10000)

    page.click("#nav-default-btn")
    expect(page.locator("#default-view")).not_to_have_class(HIDDEN_RE, timeout=10000)


def test_tailor_form_elements_present(page, app_server):
    _goto(page, app_server)
    page.click("#nav-tailor-btn")
    expect(page.locator("#company-input")).to_be_visible(timeout=10000)
    expect(page.locator("#jd-input")).to_be_visible(timeout=10000)
    expect(page.locator("#generate-btn")).to_be_visible(timeout=10000)


def test_chat_elements_present(page, app_server):
    _goto(page, app_server)
    page.click("#nav-chat-btn")
    expect(page.locator("#chatbot-view")).not_to_have_class(HIDDEN_RE, timeout=10000)
    expect(page.locator('.m3-mode-btn[data-mode="local"]')).to_be_visible(timeout=10000)
    expect(page.locator('.m3-mode-btn[data-mode="global"]')).to_be_visible(timeout=10000)
    expect(page.locator("#clear-chat-btn")).to_be_visible(timeout=10000)


def test_system_status_badge_present(page, app_server):
    _goto(page, app_server)
    expect(page.locator("#system-status")).to_be_visible(timeout=10000)
