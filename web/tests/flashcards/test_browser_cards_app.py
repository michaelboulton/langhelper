"""The Flashcards tab of the Flutter build in app/, in Chromium. It skips
unless STATIC_DIR is that build (README.md, "The Flutter app"):

STATIC_DIR=app/build/web uv run pytest tests/flashcards/test_browser_cards_app.py
"""

import re
from pathlib import Path

import pytest
from playwright.sync_api import expect
from tlhelper import app as service
from tlhelper.flashcards import decks

pytestmark = pytest.mark.skipif(
    not (service.STATIC_DIR / "flutter_bootstrap.js").is_file(),
    reason="STATIC_DIR is not a Flutter build",
)

TOML = """
name = "Basics"
language = "hr"
english_field = "Front"
answer_field = "Back"
"""
# A picture that a screenshot shows: the icon of the app.
PICTURE = (Path(__file__).parents[2] / "app/web/icon-192.png").read_bytes()
# A silent MPEG-1 layer III frame, a few times: the browser plays it with no
# error.
SILENT_MP3 = (b"\xff\xfb\x90\x00" + b"\x00" * 413) * 8


def open_tab(browser, server, width):
    # Tall, so that --screenshots shows the whole tab.
    context = browser.new_context(
        base_url=server, viewport={"width": width, "height": 1400}
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto("/#/cards")
    page.get_by_role("heading", name="Flashcards").wait_for()
    expect(page.get_by_role("tab", name="Flashcards")).to_be_visible()
    return context, page, errors


def deck_button(page):
    return page.get_by_role("button", name=re.compile("^Basics"))


def note(page, text):
    """A text of the semantics tree: a node of its own, or the aria-label of
    the group that Flutter merges it into. Not the copy in the announcement
    of a live region."""
    return (
        page.get_by_label(text)
        .or_(page.locator("flt-semantics").get_by_text(text))
        .first
    )


def screenshot(request, page, name):
    if folder := request.config.getoption("--screenshots"):
        # The canvas paints a moment after the semantics tree changes.
        page.wait_for_timeout(1000)
        page.screenshot(path=Path(folder) / f"{name}.png")


@pytest.mark.parametrize("width", [390, 1280])
def test_a_card_with_a_picture_and_a_clip(
    browser, server, deck_dir, make_apkg, request, type_into, width
):
    notes = [("guid-house", '<img src="my house.png">', "kuća[sound:kuća.mp3]")]
    media = {"my house.png": PICTURE, "kuća.mp3": SILENT_MP3}
    make_apkg(deck_dir / "basics.apkg", notes, media=media)
    (deck_dir / "basics.toml").write_text(TOML, encoding="utf-8")
    decks.import_decks()
    context, page, errors = open_tab(browser, server, width)
    with page.expect_response(re.compile("/media/my%20house.png$")) as picture:
        deck_button(page).click()
    assert picture.value.status == 200
    note(page, "Enter what you see or hear in Croatian.").wait_for()
    screenshot(request, page, f"card-picture-{width}")

    type_into(page.get_by_role("textbox"), "kuća")
    with page.expect_response(re.compile("/media/ku%C4%87a.mp3$")) as clip:
        page.get_by_role("button", name="Check").click()
        # The answer runs the light models, so the first one takes a moment.
        page.get_by_role("button", name="Next card").wait_for(timeout=60_000)
    assert clip.value.ok
    note(page, re.compile("Good: this card comes back")).wait_for()
    # The clip of the answer has its play button.
    expect(page.get_by_role("button", name=re.compile("^(Play|Pause)$"))).to_have_count(
        1
    )
    assert errors == []
    context.close()


@pytest.mark.parametrize("width", [390, 1280])
def test_an_answered_card(
    browser, server, deck_dir, make_apkg, request, type_into, width
):
    make_apkg(
        deck_dir / "basics.apkg", [("guid-coffee", "I drink coffee.", "Pijem kavu.")]
    )
    (deck_dir / "basics.toml").write_text(TOML, encoding="utf-8")
    decks.import_decks()
    context, page, errors = open_tab(browser, server, width)
    deck_button(page).click()
    note(page, "Enter this in Croatian.").wait_for()
    page.get_by_role("button", name="chip: coffee NOUN").wait_for()

    # One wrong letter: Hard.
    type_into(page.get_by_role("textbox"), "Pijem kafu.")
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Next card").wait_for(timeout=60_000)
    page.get_by_role("button", name="chip: kafu NOUN").wait_for()
    page.get_by_role("button", name="chip: kavu NOUN").wait_for()
    note(page, re.compile("Hard: this card comes back")).wait_for()
    screenshot(request, page, f"card-answered-{width}")

    # The keys 1 to 4 change the rating.
    page.keyboard.press("3")
    note(page, re.compile("Good: this card comes back")).wait_for()

    # Headless Chromium has speechSynthesis, but no voices.
    page.get_by_role("button", name="Read it aloud").click()
    note(page, "This browser has no voices, so it cannot read a text aloud.").wait_for()

    # "Next card" has the focus.
    page.get_by_role("button", name="Next card").focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Next card")).to_have_count(0)
    assert page.url.endswith("/#/cards")
    assert errors == []
    context.close()


@pytest.mark.parametrize("width", [390, 1280])
def test_explain_and_progress(
    backend, browser, server, deck_dir, make_apkg, request, type_into, width
):
    make_apkg(
        deck_dir / "basics.apkg", [("guid-coffee", "I drink coffee.", "Pijem kavu.")]
    )
    (deck_dir / "basics.toml").write_text(TOML, encoding="utf-8")
    decks.import_decks()
    context, page, errors = open_tab(browser, server, width)
    deck_button(page).click()
    note(page, "Enter this in Croatian.").wait_for()
    # No questions before the answer.
    expect(page.get_by_role("button", name="Why is my answer wrong?")).to_have_count(0)

    type_into(page.get_by_role("textbox"), "Pijem kafu.")
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Next card").wait_for(timeout=60_000)
    page.get_by_role("button", name="Why is my answer wrong?").click()
    note(page, "Answer 1.").wait_for()
    note(page, "fake-model wrote this. It can be wrong.").wait_for()
    assert len(backend.prompts) == 1
    screenshot(request, page, f"card-explain-{width}")

    # One answer, rated Hard: not "Again".
    page.get_by_role("tab", name="Progress").click()
    note(page, "Answers").wait_for()
    note(page, "100%").wait_for()
    assert page.url.endswith("/#/progress")
    screenshot(request, page, f"progress-{width}")
    assert errors == []
    context.close()
