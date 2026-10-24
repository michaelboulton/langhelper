"""One picture of the Flutter app, with no test (README.md, "Pictures of the
page"). It starts the server as conftest.py does, opens the page in Chromium,
and saves a PNG:

uv run python tests/shot.py "Ovo je rečenica." --translate --out shot.png
uv run python tests/shot.py --deck Basics --dark --out card.png

A text goes to the Breakdown tab. --deck NAME opens the next card of the
first deck whose name starts with NAME, from the deck folders of the app.
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest  # noqa: E402
from conftest import (  # noqa: E402
    APP_BUILD,
    _type_into,
    new_context,
    serve_app,
    start_server,
)
from playwright.sync_api import sync_playwright  # noqa: E402
from tlhelper import app as service  # noqa: E402
from tlhelper.flashcards import decks, store  # noqa: E402


def breakdown(page, text, translate):
    page.goto("/")
    page.get_by_role("heading", name=re.compile("sentence breakdown$")).wait_for()
    # The first request waits for the load of the light models.
    _type_into(page.get_by_role("textbox", name="Time limit"), "60")
    if translate:
        page.get_by_role("checkbox", name="Translate to English").click()
    _type_into(page.get_by_role("textbox").first, text)
    chip = page.get_by_role("button", name=re.compile("^chip: ")).first
    chip.wait_for(timeout=60_000)
    if translate:
        # The English side, or the reason that it is missing (no DeepL key).
        side = re.compile("^(English: |No translation: )")
        page.locator("flt-semantics").get_by_text(side).first.wait_for()


def card(page, name):
    page.goto("/#/cards")
    page.get_by_role("button", name=re.compile(f"^{re.escape(name)}")).click()
    page.locator("flt-semantics").get_by_text(re.compile("^Enter ")).first.wait_for()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("text", nargs="?", help="a text for the Breakdown tab")
    parser.add_argument("--deck", metavar="NAME", help="a card of this deck")
    parser.add_argument("--translate", action="store_true")
    parser.add_argument("--dark", action="store_true", help="the dark theme")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=1400)
    parser.add_argument("--out", type=Path, default=Path("shot.png"))
    args = parser.parse_args()
    if (args.text is None) == (args.deck is None):
        parser.error("give a text or --deck, not both")
    if not (APP_BUILD / "index.html").is_file():
        sys.exit(f"no Flutter build in {APP_BUILD} (README.md, 'The Flutter app')")

    with tempfile.TemporaryDirectory() as folder, pytest.MonkeyPatch.context() as patch:
        # The databases of the picture are new, and are gone after it.
        patch.setattr(service, "DB_PATH", Path(folder) / "lemmas.db")
        patch.setattr(store, "DB_PATH", Path(folder) / "flashcards.db")
        if args.deck:
            decks.import_decks()
        serve_app(APP_BUILD, patch)
        address, stop = start_server()
        try:
            with sync_playwright() as playwright:
                # Chromium cannot make its own sandbox inside a container.
                browser = playwright.chromium.launch(args=["--no-sandbox"])
                context = new_context(
                    browser,
                    address,
                    width=args.width,
                    height=args.height,
                    dark=args.dark,
                )
                page = context.new_page()
                if args.deck:
                    card(page, args.deck)
                else:
                    breakdown(page, args.text, args.translate)
                # The canvas paints a moment after the semantics tree changes.
                page.wait_for_timeout(1000)
                page.screenshot(path=args.out)
                browser.close()
        finally:
            stop()
    print(args.out)


if __name__ == "__main__":
    main()
