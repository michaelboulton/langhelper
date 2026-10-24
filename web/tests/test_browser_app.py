"""The smoke test of the Flutter build in app/. It skips unless STATIC_DIR is
that build (README.md, "The Flutter app"):

STATIC_DIR=app/build/web uv run pytest tests/test_browser_app.py
"""

from pathlib import Path

import pytest
from playwright.sync_api import expect
from tlhelper import app as service
from tlhelper import translators

pytestmark = pytest.mark.skipif(
    not (service.STATIC_DIR / "flutter_bootstrap.js").is_file(),
    reason="STATIC_DIR is not a Flutter build",
)


class FakeTranslator:
    name = "fake"

    def translate(self, text, source, target):
        return {"Ona je je bila kod kuće.": "She was at home."}[text]


@pytest.fixture(autouse=True)
def translator(monkeypatch):
    monkeypatch.setitem(translators.TRANSLATORS, "fake", FakeTranslator())
    monkeypatch.setenv("TRANSLATOR", "fake")


def test_the_app_loads_with_no_request_outside_the_origin(browser, server):
    context = browser.new_context(base_url=server)
    page = context.new_page()
    requests, errors = [], []
    page.on("request", lambda request: requests.append(request.url))
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto("/")
    page.get_by_role("heading", name="Croatian sentence breakdown").wait_for()
    page.wait_for_load_state("networkidle")
    # The headers of the middleware: skwasm runs multithreaded.
    assert page.evaluate("crossOriginIsolated")
    outside = [
        url for url in requests if not url.startswith((f"{server}/", "data:", "blob:"))
    ]
    assert outside == []
    assert errors == []
    context.close()


def type_into(field, text):
    """Type into a text field of the app. Flutter connects the field a moment
    after the browser focuses it, and drops the keys of that moment."""
    field.click()
    expect(field).to_be_focused()
    field.page.wait_for_timeout(500)
    field.press("ControlOrMeta+a")
    field.press_sequentially(text)
    expect(field).to_have_value(text)


@pytest.mark.parametrize("width", [390, 1280])
def test_the_breakdown_of_a_sentence(browser, server, request, width):
    # Tall, so that --screenshots shows the whole tab.
    context = browser.new_context(
        base_url=server, viewport={"width": width, "height": 1400}
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto("/")
    page.get_by_role("heading", name="Croatian sentence breakdown").wait_for()
    # The first request waits for the load of the model.
    type_into(page.get_by_role("textbox", name="Time limit"), "60")
    # The screenshot shows the curves to the translation.
    page.get_by_role("checkbox", name="Translate to English").click()
    type_into(page.get_by_role("textbox").first, "Ona je je bila kod kuće.")
    page.get_by_role("button", name="chip: Ona PRON").wait_for()
    page.get_by_role("button", name="chip: She PRON").wait_for()
    page.get_by_role("button", name="chip: je AUX").last.click()
    page.get_by_text("'je' repeats.").wait_for()
    if folder := request.config.getoption("--screenshots"):
        # The border of the selected chip shows after the ink of the tap.
        page.wait_for_timeout(1000)
        page.screenshot(path=Path(folder) / f"breakdown-{width}.png")
    assert errors == []
    context.close()


def test_the_locale_of_the_address(browser, server):
    context = browser.new_context(base_url=server)
    page = context.new_page()
    page.goto("/?locale=hr")
    page.get_by_role("heading", name="Raščlamba rečenice: hrvatski").wait_for()
    context.close()


def test_the_locale_of_the_browser(browser, server):
    context = browser.new_context(base_url=server, locale="de-AT")
    page = context.new_page()
    page.goto("/")
    page.get_by_role("heading", name="Satzanalyse: Kroatisch").wait_for()
    context.close()
