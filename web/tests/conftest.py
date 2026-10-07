"""The browser for the tests of the page, and the folders of the app data.

The browser tests need the browser of Playwright once:
uv run playwright install --only-shell chromium
With no browser, they skip. With --screenshots=DIR, each page of a browser test
saves a picture of itself to DIR at the end of the test (README.md, "Running
locally").
"""

import base64
import hashlib
import os
import re
import shlex
import threading
import time
import urllib.request
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import Error, sync_playwright
from tlhelper import app as service
from tlhelper.flashcards import decks, store

# index.html loads the Fluent script from here.
CDN = "https://cdn.jsdelivr.net/**"


def pytest_addoption(parser):
    parser.addoption(
        "--screenshots",
        metavar="DIR",
        help="save a picture of each page of a browser test to DIR",
    )


@pytest.fixture
def deck_dir(tmp_path, monkeypatch):
    """An empty deck folder and an empty database."""
    folder = tmp_path / "decks"
    folder.mkdir()
    monkeypatch.setattr(decks, "DECK_DIRS", [folder])
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "flashcards.db")
    return folder


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    """fake_claude(stdout, code=0, stderr="", sleep=0): a `claude` command
    on the PATH, for the Claude Code backend (tlhelper/explain/claude_cli.py).
    It keeps its arguments and its stdin in the folder it returns."""
    folder = tmp_path / "claude-cli"
    folder.mkdir()
    monkeypatch.setenv("PATH", f"{folder}:{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CLAUDE_DIR", str(folder))

    def use(stdout, code=0, stderr="", sleep=0):
        script = folder / "claude"
        script.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$@" > "$FAKE_CLAUDE_DIR/args"\n'
            'cat > "$FAKE_CLAUDE_DIR/prompt"\n'
            f"sleep {sleep}\n"
            f"printf '%s' {shlex.quote(stderr)} >&2\n"
            f"printf '%s' {shlex.quote(stdout)}\n"
            f"exit {code}\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return folder

    return use


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        try:
            # Chromium cannot make its own sandbox inside a container.
            browser = playwright.chromium.launch(args=["--no-sandbox"])
        except Error as exc:
            pytest.skip(f"no browser (uv run playwright install chromium): {exc}")
        yield browser
        browser.close()


@pytest.fixture
def server(deck_dir, monkeypatch):
    """The address of the app. The server is a thread of this process, so it
    sees the deck folder and the databases of the test. No lifespan: no model
    warm-up, and no import of the real decks."""
    monkeypatch.setattr(service, "DB_PATH", deck_dir.parent / "lemmas.db")
    monkeypatch.delenv("TLHELPER_ALWAYS_LARGE", raising=False)
    config = uvicorn.Config(
        service.app, host="127.0.0.1", port=0, lifespan="off", log_level="warning"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        assert thread.is_alive(), "the server did not start"
        time.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://localhost:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def fluent_script(request):
    """The Fluent script that index.html loads from the CDN, or None with no
    network. The file stays in the cache of pytest, and it must have the hash
    of the integrity attribute: the browser refuses another file."""
    html = service.INDEX_HTML.read_text(encoding="utf-8")
    url = re.search(r'src="(https://cdn\.jsdelivr\.net/[^"]+)"', html).group(1)
    integrity = re.search(r'integrity="sha384-([^"]+)"', html).group(1)
    cached = request.config.cache.mkdir("fluent") / url.rsplit("@", 1)[1].replace(
        "/", "-"
    )
    if not cached.is_file():
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                cached.write_bytes(response.read())
        except OSError:
            return None
    data = cached.read_bytes()
    assert base64.b64encode(hashlib.sha384(data).digest()).decode() == integrity
    return data


@pytest.fixture
def new_page(browser, server, fluent_script, request):
    """Opens a page: new_page(locale="en-US", fluent=True, ignore=None).
    fluent=False: the CDN does not answer. ignore: a text, and an error with
    that text is not a failure. At the end of the test, each page saves its
    picture (--screenshots), closes, and must have no errors."""
    opened = []

    def open_page(locale="en-US", fluent=True, ignore=None):
        script = fluent_script if fluent else None
        context = browser.new_context(base_url=server, locale=locale)

        # The tests must not need the network. Without the script, the page
        # uses its own formatter for the English text (static/js/i18n.js).
        def cdn(route):
            if script is None:
                return route.abort()
            return route.fulfill(
                body=script,
                content_type="application/javascript",
                headers={"access-control-allow-origin": "*"},
            )

        context.route(CDN, cdn)
        page = context.new_page()
        errors = []

        def error(text):
            if ignore is None or ignore not in text:
                errors.append(text)

        page.on("pageerror", lambda exc: error(str(exc)))

        def console(message):
            # The browser reports the script that did not load.
            from_cdn = message.location.get("url", "").startswith(CDN[:-2])
            if message.type == "error" and not from_cdn:
                error(message.text)

        page.on("console", console)
        opened.append((page, errors))
        return page

    yield open_page
    folder = request.config.getoption("--screenshots")
    for number, (page, errors) in enumerate(opened):
        if folder:
            name = re.sub(r"[^\w.-]+", "_", request.node.name)
            if number:
                name += f"-{number + 1}"
            path = Path(folder) / f"{name}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=path, full_page=True)
        page.context.close()
        assert errors == [], request.node.name


@pytest.fixture
def page(new_page):
    return new_page()
