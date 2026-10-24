"""The browser for the tests of the page, the folders of the app data, and a
fake AI service for the tools in scripts/.

The browser tests open the Flutter build in STATIC_DIR (default
app/build/web), and need the browser of Playwright once:
uv run playwright install --only-shell chromium
With no browser or no build, they skip. With --screenshots=DIR, each page of a
browser test saves a picture of itself to DIR at the end of the test
(README.md, "The browser tests").
"""

import json
import os
import re
import shlex
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import Error, expect, sync_playwright
from scripts import lessons
from tlhelper import app as service
from tlhelper import explain
from tlhelper.flashcards import decks, store

# flutter build web --wasm --no-web-resources-cdn --base-href /static/
APP_BUILD = service.STATIC_DIR

# A click on the placeholder of Flutter turns on the semantics tree, as for a
# screen reader. The app leaves it off (README.md, "The browser tests").
SEMANTICS_ON = """
new MutationObserver((_, observer) => {
  const placeholder = document.querySelector("flt-semantics-placeholder");
  if (placeholder) {
    observer.disconnect();
    placeholder.click();
  }
}).observe(document, { childList: true, subtree: true });
"""


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


class ScriptedBackend:
    """Gives its answers in order, and keeps what it was asked."""

    name = "scripted"

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []
        self.systems = []
        self.kwargs = []

    def available(self):
        return True

    def model(self):
        return "scripted-model"

    def complete(self, system, prompt, **kwargs):
        self.systems.append(system)
        self.prompts.append(prompt)
        self.kwargs.append(kwargs)
        assert self.answers, "one request too many"
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer)


@pytest.fixture
def scripted(monkeypatch):
    """scripted(*answers): the AI service of the next run of a script in
    scripts/."""

    def use(*answers):
        backend = ScriptedBackend(answers)
        monkeypatch.setitem(explain.BACKENDS, "scripted", backend)
        monkeypatch.setenv("TLHELPER_AI_BACKEND", "scripted")
        return backend

    return use


@pytest.fixture
def fake_lemmas(monkeypatch):
    """Each word of the tagged text is a noun: no model load."""

    def lemmas_of(text, language):
        words = sorted({word.strip(".").lower() for word in text.split()})
        return {"NOUN": words} if words else {}

    monkeypatch.setattr(lessons, "lemmas_of", lemmas_of)


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
def app_build():
    """The folder of the Flutter build. Without it, the tests of the page
    skip."""
    if not (APP_BUILD / "index.html").is_file():
        pytest.skip(f"no Flutter build in {APP_BUILD} (README.md, 'Running locally')")
    return APP_BUILD


@pytest.fixture(scope="session")
def browser(app_build):
    with sync_playwright() as playwright:
        try:
            # Chromium cannot make its own sandbox inside a container.
            browser = playwright.chromium.launch(args=["--no-sandbox"])
        except Error as exc:
            pytest.skip(f"no browser (uv run playwright install chromium): {exc}")
        yield browser
        browser.close()


def start_server():
    """Starts the app in a thread of this process, so it sees the deck folder
    and the databases of the caller. No lifespan: no model warm-up, and no
    import of the real decks. Returns the address and a function that stops
    the server."""
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

    def stop():
        server.should_exit = True
        thread.join(timeout=5)

    return f"http://localhost:{port}", stop


@pytest.fixture
def server(app_build, deck_dir, monkeypatch):
    """The address of the app."""
    monkeypatch.setattr(service, "DB_PATH", deck_dir.parent / "lemmas.db")
    monkeypatch.delenv("TLHELPER_ALWAYS_LARGE", raising=False)
    address, stop = start_server()
    yield address
    stop()


def new_context(
    browser, server, *, locale="en-US", width=1280, height=1400, dark=False
):
    """A browser context with no network: a request outside the server fails.
    Tall, so that a picture shows the whole tab."""
    context = browser.new_context(
        base_url=server,
        locale=locale,
        viewport={"width": width, "height": height},
        color_scheme="dark" if dark else "light",
    )
    context.route(
        lambda url: not url.startswith(f"{server}/"), lambda route: route.abort()
    )
    context.route("**/static/flutter_bootstrap.js", _single_threaded)
    context.add_init_script(SEMANTICS_ON)
    return context


def _single_threaded(route):
    """skwasm on one thread: on more threads, the page crashes now and then
    (README.md, "The browser tests")."""
    response = route.fetch()
    body = response.text().replace(
        "_flutter.loader.load({",
        "_flutter.loader.load({config: {forceSingleThreadedSkwasm: true},",
    )
    route.fulfill(response=response, body=body)


def _type_into(field, text):
    field.click()
    expect(field).to_be_focused()
    field.page.wait_for_timeout(500)
    field.press("ControlOrMeta+a")
    field.press_sequentially(text)
    expect(field).to_have_value(text)


@pytest.fixture
def type_into():
    """type_into(field, text): type into a text field of the Flutter app.
    Flutter connects the field a moment after the browser focuses it, and
    drops the keys of that moment."""
    return _type_into


@pytest.fixture
def note():
    """note(page, text): a text of the semantics tree, as a node of its own or
    as the aria-label of the group that Flutter merges it into. Not the copy
    in the announcement of a live region. text can be a regex."""

    def find(page, text):
        return (
            page.get_by_label(text)
            .or_(page.locator("flt-semantics").get_by_text(text))
            .first
        )

    return find


def _save(page, path):
    # The canvas paints a moment after the semantics tree changes.
    page.wait_for_timeout(1000)
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=path)


@pytest.fixture
def screenshot(request):
    """screenshot(page, name): with --screenshots=DIR, a picture of the page
    now, as DIR/name.png."""
    folder = request.config.getoption("--screenshots")

    def take(page, name):
        if folder:
            _save(page, Path(folder) / f"{name}.png")

    return take


@pytest.fixture
def new_page(browser, server, request):
    """Opens a page: new_page(locale="en-US", width=1280, height=1400,
    dark=False, ignore=None). ignore: a text, and an error with that text is
    not a failure. At the end of the test, each page saves its picture
    (--screenshots), closes, and must have no errors."""
    opened = []

    def open_page(locale="en-US", width=1280, height=1400, dark=False, ignore=None):
        context = new_context(
            browser, server, locale=locale, width=width, height=height, dark=dark
        )
        page = context.new_page()
        errors = []

        def error(text):
            if ignore is None or ignore not in text:
                errors.append(text)

        page.on("pageerror", lambda exc: error(str(exc)))

        def console(message):
            if message.type == "error":
                error(f"{message.text} {message.location.get('url', '')}")

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
            _save(page, Path(folder) / f"{name}.png")
        page.context.close()
        assert errors == [], request.node.name


@pytest.fixture
def page(new_page):
    return new_page()
