"""The smoke tests of the Flutter build in app/: it loads with no request
outside the origin, and its text and its theme follow the browser. The
browser fixtures are in conftest.py."""

import base64

from tlhelper import app as service


def test_the_app_loads_with_no_request_outside_the_origin(page, server):
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    page.goto("/")
    page.get_by_role("heading", name="Croatian sentence breakdown").wait_for()
    page.wait_for_load_state("networkidle")
    # The headers of the middleware: skwasm runs multithreaded.
    assert page.evaluate("crossOriginIsolated")
    outside = [
        url for url in requests if not url.startswith((f"{server}/", "data:", "blob:"))
    ]
    assert outside == []


def test_the_page_is_the_flutter_build(page, app_build):
    assert service.INDEX_HTML == app_build / "index.html"
    response = page.goto("/static/flutter_bootstrap.js")
    assert response.ok


def test_the_locale_of_the_address(page):
    page.goto("/?locale=hr")
    page.get_by_role("heading", name="Raščlamba rečenice: hrvatski").wait_for()


def test_the_locale_of_the_browser(new_page):
    page = new_page(locale="de-AT")
    page.goto("/")
    page.get_by_role("heading", name="Satzanalyse: Kroatisch").wait_for()


def corner_brightness(page):
    """The sum of red, green and blue of the top left pixel of the page: the
    background of the app bar. The browser decodes the PNG."""
    page.goto("/")
    page.get_by_role("heading", name="Croatian sentence breakdown").wait_for()
    # The canvas paints a moment after the semantics tree.
    page.wait_for_timeout(1000)
    shot = page.screenshot(clip={"x": 0, "y": 0, "width": 4, "height": 4})
    return sum(
        page.evaluate(
            """async (data) => {
                const image = new Image();
                image.src = "data:image/png;base64," + data;
                await image.decode();
                const context = new OffscreenCanvas(1, 1).getContext("2d");
                context.drawImage(image, 0, 0);
                return Array.from(context.getImageData(0, 0, 1, 1).data.slice(0, 3));
            }""",
            base64.b64encode(shot).decode(),
        )
    )


def test_the_theme_follows_the_browser(new_page):
    light = corner_brightness(new_page())
    dark = corner_brightness(new_page(dark=True))
    assert dark < 3 * 128 < light
