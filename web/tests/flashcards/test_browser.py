"""The Flashcards, Explain and Progress parts of the Flutter app in a real
browser, against a server in this process. The browser fixtures are in
tests/conftest.py.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect
from tlhelper import app as service
from tlhelper import explain
from tlhelper.flashcards import decks, routes, store

TOML = """
name = "Basics"
language = "hr"
english_field = "Front"
answer_field = "Back"
"""
COFFEE = [("guid-coffee", "I drink coffee.", "Pijem kavu.")]
# A picture that a screenshot shows: the icon of the app.
PICTURE = (Path(__file__).parents[2] / "app/web/icon-192.png").read_bytes()
# A silent MPEG-1 layer III frame, a few times: the browser plays it with no
# error.
SILENT_MP3 = (b"\xff\xfb\x90\x00" + b"\x00" * 413) * 8
ACCENTS = re.compile("^Accent marks:")


def add_deck(deck_dir, make_apkg, notes, **options):
    make_apkg(deck_dir / "basics.apkg", notes, **options)
    (deck_dir / "basics.toml").write_text(TOML, encoding="utf-8")
    decks.import_decks()


def open_tab(page, path="/#/cards"):
    page.goto(path)
    page.get_by_role("tab", name=re.compile("^(Flashcards|Kartice)$")).wait_for()


def deck_button(page, name="Basics"):
    return page.get_by_role("button", name=re.compile(f"^{name}"))


def answer_as(user, rating):
    card = store.next_card(user, 1)["card"]
    store.answer(user, card["id"], rating, "", None)


def answer(page, type_into, text):
    """Send an answer, and wait for its result. The answer runs the light
    models, so the first one takes a moment."""
    type_into(page.get_by_role("textbox"), text)
    page.get_by_role("button", name="Check").click()
    page.get_by_role("button", name="Next card").wait_for(timeout=60_000)


def rating(page, name):
    return page.get_by_role("button", name=name, exact=True)


def test_the_tabs(page, note):
    page.goto("/")
    expect(page.get_by_role("tab", name="Breakdown")).to_have_attribute(
        "aria-selected", "true"
    )
    page.get_by_role("tab", name="Flashcards").click()
    page.get_by_role("heading", name="Flashcards").wait_for()
    note(page, re.compile("^No decks.")).wait_for()
    assert page.url.endswith("/#/cards")
    page.get_by_role("tab", name="Progress").click()
    note(page, "No answers yet.").wait_for()
    assert page.url.endswith("/#/progress")
    page.get_by_role("tab", name="Breakdown").click()
    page.get_by_role("heading", name="Croatian sentence breakdown").wait_for()
    assert urlparse(page.url).fragment in ("", "/")


def test_the_page_in_the_language_of_the_browser(new_page, deck_dir, make_apkg):
    add_deck(
        deck_dir,
        make_apkg,
        [("guid-1", "I drink.", "Pijem."), ("guid-2", "I eat.", "Jedem.")],
    )
    page = new_page(locale="hr-HR")
    open_tab(page)
    expect(page.get_by_role("tab", name="Kartice")).to_be_visible()
    # Croatian has a form for 2 to 4: "2 kartice", but "5 kartica".
    expect(deck_button(page)).to_contain_text("2 kartice")


def test_the_progress_of_the_user(page, deck_dir, make_apkg, note):
    add_deck(deck_dir, make_apkg, COFFEE)
    answer_as(routes.LOCAL_USER, 3)
    answer_as("user-2", 1)
    page.goto("/#/progress")
    note(page, "Answers").wait_for()
    # 1 of 1 was not "Again".
    note(page, "100%").wait_for()
    # Not an admin: no other user.
    expect(note(page, "Cards of")).to_have_count(0)


def test_an_admin_selects_another_user(page, deck_dir, make_apkg, note):
    add_deck(deck_dir, make_apkg, COFFEE)
    answer_as(routes.LOCAL_USER, 3)
    answer_as("user-2", 1)
    store.save_user("user-2", "Ana")
    service.app.dependency_overrides[routes.is_admin] = lambda: True
    try:
        page.goto("/#/progress")
        note(page, "Cards of").wait_for()
        note(page, "100%").wait_for()
        page.get_by_role("button", name=re.compile("My cards")).click()
        page.get_by_role("menuitem", name="Ana").or_(
            page.get_by_role("button", name="Ana")
        ).last.click()
        note(page, "0%").wait_for()
    finally:
        service.app.dependency_overrides.pop(routes.is_admin)


@pytest.mark.parametrize("width", [390, 1280])
def test_the_flow_of_a_card(
    new_page, deck_dir, make_apkg, note, screenshot, type_into, width
):
    add_deck(deck_dir, make_apkg, COFFEE)
    page = new_page(width=width)
    open_tab(page)
    deck_button(page).click()
    note(page, "Enter this in Croatian.").wait_for()
    page.get_by_role("button", name="chip: coffee NOUN").wait_for()
    expect(page.get_by_role("button", name="Next card")).to_have_count(0)

    # One wrong letter: Hard.
    type_into(page.get_by_role("textbox"), "Pijem kafu.")
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Next card").wait_for(timeout=60_000)
    page.get_by_role("button", name="chip: kafu NOUN").wait_for()
    page.get_by_role("button", name="chip: kavu NOUN").wait_for()
    expect(rating(page, "2 Hard")).to_have_attribute("aria-current", "true")
    note(page, re.compile("Hard: this card comes back")).wait_for()
    # The curves from the answers to the prompt.
    note(page, re.compile(r"^links: \d+$")).wait_for()
    screenshot(page, f"card-answered-{width}")

    # The keys 1 to 4 change the rating.
    page.keyboard.press("3")
    note(page, re.compile("Good: this card comes back")).wait_for()
    expect(rating(page, "3 Good")).to_have_attribute("aria-current", "true")

    # Headless Chromium has speechSynthesis, but no voices. A browser with no
    # voices must say so, and not stay silent.
    page.get_by_role("button", name="Read it aloud").click()
    note(page, "This browser has no voices, so it cannot read a text aloud.").wait_for()

    # "Next card" has the focus.
    page.get_by_role("button", name="Next card").focus()
    page.keyboard.press("Enter")
    note(page, "No more cards for now.").wait_for()
    expect(page.get_by_role("button", name="Next card")).to_have_count(0)
    assert page.url.endswith("/#/cards")


def test_no_questions_to_the_ai_with_no_key(page, deck_dir, make_apkg, backend):
    backend.key = False
    add_deck(deck_dir, make_apkg, COFFEE)
    open_tab(page)
    deck_button(page).click()
    page.get_by_role("button", name="I do not know").click()
    page.get_by_role("button", name="Next card").wait_for(timeout=60_000)
    expect(page.get_by_role("button", name="Why is my answer wrong?")).to_have_count(0)


@pytest.mark.parametrize("width", [390, 1280])
def test_a_question_to_the_ai(
    new_page,
    deck_dir,
    make_apkg,
    backend,
    monkeypatch,
    note,
    screenshot,
    type_into,
    width,
):
    # The model can write anything: the page must show it as text.
    monkeypatch.setattr(
        backend, "complete", lambda system, prompt: "<b>kavu</b> is the\naccusative."
    )
    add_deck(deck_dir, make_apkg, COFFEE)
    page = new_page(width=width)
    open_tab(page)
    deck_button(page).click()
    note(page, "Enter this in Croatian.").wait_for()
    # No questions before the answer.
    why = page.get_by_role("button", name="Why is my answer wrong?")
    expect(why).to_have_count(0)
    answer(page, type_into, "Pijem kafu.")
    # A card has the questions about an answer and those about a sentence.
    questions = [
        "What does this mean?",
        "Explain the grammar",
        "Is this colloquial?",
        "Why is my answer wrong?",
        "Is my answer also correct?",
        "What is the difference?",
    ]
    for each in questions:
        expect(page.get_by_role("button", name=each)).to_be_visible()
    type_into(page.get_by_role("textbox"), "why not kafu?")
    why.click()
    note(page, "<b>kavu</b> is the\naccusative.").wait_for()
    note(page, "fake-model wrote this. It can be wrong.").wait_for()
    screenshot(page, f"card-explain-{width}")
    # The next card has no answer yet, and so no questions.
    page.get_by_role("button", name="Next card").click()
    note(page, "No more cards for now.").wait_for()
    expect(why).to_have_count(0)


def test_the_breakdown_has_only_the_questions_about_a_sentence(
    page, backend, type_into
):
    page.goto("/")
    type_into(page.get_by_role("textbox").first, "Idemo na kavu.")
    page.get_by_role("button", name="chip: kavu NOUN").wait_for(timeout=60_000)
    expect(page.get_by_role("button", name="Explain the grammar")).to_be_visible()
    expect(page.get_by_role("button", name="Why is my answer wrong?")).to_have_count(0)


def test_a_question_to_the_ai_again_after_an_error(
    new_page, deck_dir, make_apkg, backend, monkeypatch, note, type_into
):
    answers = iter(
        [explain.ExplainError("the AI service returned HTTP 502"), "It is fine."]
    )

    def complete(system, prompt, **kwargs):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(backend, "complete", complete)
    # The browser reports the 502 in the console.
    page = new_page(ignore="502")
    add_deck(deck_dir, make_apkg, COFFEE)
    open_tab(page)
    deck_button(page).click()
    answer(page, type_into, "Pijem kafu.")
    why = page.get_by_role("button", name="Why is my answer wrong?")
    why.click()
    note(page, re.compile("502")).wait_for()
    expect(why).to_be_enabled()
    why.click()
    note(page, "It is fine.").wait_for()


def test_a_language_from_right_to_left(page, deck_dir, make_apkg, type_into):
    # No language of the app has such a script, so the page gets Croatian as
    # one. The direction comes only from the language list.
    def right_to_left(route):
        response = route.fetch()
        languages = response.json()
        for each in languages["languages"]:
            if each["code"] == "hr":
                each["direction"] = "rtl"
        route.fulfill(response=response, body=json.dumps(languages))

    page.route("**/api/v1/languages", right_to_left)
    add_deck(deck_dir, make_apkg, COFFEE)
    open_tab(page)
    deck_button(page).click()
    answer(page, type_into, "Pijem kavu.")
    # The first word of a right-to-left line is on the right.
    first = page.get_by_role("button", name=re.compile("^chip: Pijem ")).first
    second = page.get_by_role("button", name="chip: kavu NOUN").first
    assert first.bounding_box()["x"] > second.bounding_box()["x"]
    # The English line is from left to right.
    english = page.get_by_role("button", name="chip: I PRON")
    drink = page.get_by_role("button", name="chip: drink VERB")
    assert english.bounding_box()["x"] < drink.bounding_box()["x"]


def test_the_accent_note_follows_the_language_of_the_deck(
    page, deck_dir, make_apkg, note
):
    make_apkg(
        deck_dir / "german.apkg", [("guid-tea", "I drink tea.", "Ich trinke Tee.")]
    )
    german = TOML.replace('"Basics"', '"Deutsch"').replace('"hr"', '"de"')
    (deck_dir / "german.toml").write_text(german, encoding="utf-8")
    add_deck(deck_dir, make_apkg, COFFEE)
    accents = note(page, ACCENTS)
    # The breakdown tab has Croatian, the first language.
    page.goto("/")
    accents.wait_for()
    page.get_by_role("tab", name="Flashcards").click()
    deck_button(page, "Deutsch").wait_for()
    expect(accents).to_have_count(0)
    deck_button(page, "Deutsch").click()
    page.get_by_role("button", name="chip: tea NOUN").wait_for()
    expect(accents).to_have_count(0)
    page.get_by_role("button", name="All decks").click()
    deck_button(page).click()
    page.get_by_role("button", name="chip: coffee NOUN").wait_for()
    accents.wait_for()


def test_the_subdecks_are_a_tree(page, deck_dir, make_apkg, note):
    notes = [
        ("guid-a", "I drink coffee.", "Pijem kavu.", 11),
        ("guid-b", "Yes, yes.", "Da, da.", 12),
        ("guid-c", "What is it?", "Što je to?", 13),
    ]
    anki_decks = {11: "Neri::Read::2", 12: "Neri::Read::3", 13: "Neri::Speak::2"}
    make_apkg(deck_dir / "basics.apkg", notes, anki_decks=anki_decks)
    (deck_dir / "basics.toml").write_text(
        TOML + 'subdecks = true\nto_english_notetypes = ["Basic"]\n', encoding="utf-8"
    )
    decks.import_decks()
    open_tab(page)
    for name in ("Basics", "Read", "Speak"):
        page.get_by_role("heading", name=name).wait_for()
    note(page, re.compile("^3 decks · 3 new")).wait_for()
    # The decks in the order of the tree, each with the last part of its name.
    names = page.get_by_role("button", name=re.compile(r"^\d\s+Croatian")).all()
    assert [each.text_content()[0] for each in names] == ["2", "3", "2"]
    names[0].click()
    note(page, "Basics › Read › 2").wait_for()
    # A note type for reading shows the Croatian.
    note(page, "Enter this in English.").wait_for()
    page.get_by_role("button", name=re.compile("^chip: Pijem ")).wait_for()


def test_a_listen_card_shows_its_text_after_the_answer(
    page, deck_dir, make_apkg, clock, note, type_into
):
    notes = [("guid-coffee", "I drink coffee.", "Pijem kavu.[sound:kava.mp3]")]
    make_apkg(deck_dir / "basics.apkg", notes, media={"kava.mp3": SILENT_MP3})
    (deck_dir / "basics.toml").write_text(TOML + "listen = true\n", encoding="utf-8")
    decks.import_decks()
    # The card of the other direction, out of the way: Easy, and a day ago.
    answer_as(routes.LOCAL_USER, 4)
    clock.add(days=1)
    open_tab(page)
    with page.expect_response(re.compile("/media/kava.mp3$")):
        deck_button(page).click()
    note(page, "Enter what you see or hear in English.").wait_for()
    pijem = page.get_by_role("button", name=re.compile("^chip: Pijem "))
    expect(pijem).to_have_count(0)
    page.get_by_role("button", name=re.compile("^(Play|Pause)$")).wait_for()
    # The canvas has the seek bar of the loaded clip.
    page.wait_for_timeout(500)

    # The player of the clip must not take the focus from the answer field.
    answer(page, type_into, "I drink coffee.")
    expect(rating(page, "3 Good")).to_have_attribute("aria-current", "true")
    # The text of the clip is in Croatian, and between the two answers.
    typed, correct = page.get_by_role("button", name="chip: I PRON").all()
    rows = [each.bounding_box()["y"] for each in (typed, pijem, correct)]
    assert rows == sorted(rows)


@pytest.mark.parametrize("width", [390, 1280])
def test_a_card_with_a_picture_and_a_clip(
    new_page, deck_dir, make_apkg, note, screenshot, type_into, width
):
    notes = [("guid-house", '<img src="my house.png">', "kuća[sound:kuća.mp3]")]
    media = {"my house.png": PICTURE, "kuća.mp3": SILENT_MP3}
    add_deck(deck_dir, make_apkg, notes, media=media)
    page = new_page(width=width)
    open_tab(page)
    with page.expect_response(re.compile("/media/my%20house.png$")) as picture:
        deck_button(page).click()
    assert picture.value.status == 200
    note(page, "Enter what you see or hear in Croatian.").wait_for()
    # The clip comes only with the answer.
    expect(page.get_by_role("button", name=re.compile("^(Play|Pause)$"))).to_have_count(
        0
    )
    screenshot(page, f"card-picture-{width}")

    with page.expect_response(re.compile("/media/ku%C4%87a.mp3$")) as clip:
        answer(page, type_into, "kuća")
    assert clip.value.ok
    expect(rating(page, "3 Good")).to_have_attribute("aria-current", "true")
    expect(page.get_by_role("button", name=re.compile("^(Play|Pause)$"))).to_have_count(
        1
    )


@pytest.mark.parametrize("width", [390, 1280])
def test_the_progress_tab(
    new_page, deck_dir, make_apkg, backend, note, type_into, width
):
    add_deck(deck_dir, make_apkg, COFFEE)
    page = new_page(width=width)
    open_tab(page)
    deck_button(page).click()
    answer(page, type_into, "Pijem kafu.")
    # One answer, rated Hard: not "Again".
    page.get_by_role("tab", name="Progress").click()
    note(page, "Answers").wait_for()
    note(page, "100%").wait_for()
    assert page.url.endswith("/#/progress")
