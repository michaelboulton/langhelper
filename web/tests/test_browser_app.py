"""The smoke test of the Flutter build in app/. It skips unless STATIC_DIR is
that build (README.md, "The Flutter app"):

STATIC_DIR=app/build/web uv run pytest tests/test_browser_app.py
"""

import pytest
from tlhelper import app as service

pytestmark = pytest.mark.skipif(
    not (service.STATIC_DIR / "flutter_bootstrap.js").is_file(),
    reason="STATIC_DIR is not a Flutter build",
)


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
