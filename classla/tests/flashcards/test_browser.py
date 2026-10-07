"""The flashcard page in a real browser, against a server in this process.
The browser fixtures are in tests/conftest.py.
"""

import base64
import threading

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
# One transparent pixel: the browser must be able to decode the picture.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg=="
)


def add_deck(deck_dir, make_apkg, notes, **options):
    make_apkg(deck_dir / "basics.apkg", notes, **options)
    (deck_dir / "basics.toml").write_text(TOML, encoding="utf-8")
    decks.import_decks()


def test_the_tabs(page):
    page.goto("/")
    expect(page.locator("#tab-breakdown")).to_be_visible()
    expect(page.locator("#tab-cards")).to_be_hidden()
    page.get_by_role("button", name="Flashcards").click()
    expect(page.locator("#tab-cards")).to_be_visible()
    expect(page.locator("#tab-breakdown")).to_be_hidden()
    assert page.url.endswith("#cards")
    expect(page.locator("#cards-status")).to_contain_text("No decks")
    page.get_by_role("button", name="Progress").click()
    expect(page.locator("#tab-progress")).to_be_visible()
    expect(page.locator("#tab-cards")).to_be_hidden()
    assert page.url.endswith("#progress")
    expect(page.locator("#progress-status")).to_have_text("No answers yet.")
    expect(page.locator("#stats")).to_be_hidden()
    # The legend of the parts of speech is only under words.
    expect(page.locator("#legend")).to_be_hidden()
    page.get_by_role("button", name="Breakdown").click()
    expect(page.locator("#legend")).to_be_visible()


def test_the_page_in_the_language_of_the_browser(
    new_page, fluent_script, deck_dir, make_apkg
):
    if fluent_script is None:
        pytest.skip("no Fluent script: the page only has its English text")
    add_deck(
        deck_dir,
        make_apkg,
        [("guid-1", "I drink.", "Pijem."), ("guid-2", "I eat.", "Jedem.")],
    )
    page = new_page(locale="hr-HR")
    page.goto("/#cards")
    expect(page.locator("html")).to_have_attribute("lang", "hr")
    expect(page.locator("#locale")).to_have_value("hr")
    expect(page.locator("#tabs button").nth(1)).to_have_text("Kartice")
    # Croatian has a form for 2 to 4: "2 kartice", but "5 kartica".
    expect(page.locator("#deck-list .deck")).to_contain_text("2 kartice")
    # The choice of the user wins over the language of the browser.
    page.locator("#locale").select_option("de")
    expect(page.locator("html")).to_have_attribute("lang", "de")
    expect(page.locator("#tabs button").nth(1)).to_have_text("Karteikarten")
    assert "locale=de" in page.url


def test_the_page_with_no_fluent_script(new_page, deck_dir, make_apkg):
    """The CDN does not answer: the page formats the English catalog itself."""
    add_deck(deck_dir, make_apkg, [("guid-1", "I drink.", "Pijem.")])
    page = new_page(locale="hr-HR", fluent=False)
    page.goto("/#cards")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.locator(".locale")).to_be_hidden()
    expect(page.locator("#deck-list .deck")).to_contain_text("Croatian · 1 card")
    expect(page.locator("#deck-list .deck")).to_contain_text("1 new · 0 in learning")


def answer_as(user, rating):
    card = store.next_card(user, 1)["card"]
    store.answer(user, card["id"], rating, "", None)


def test_the_progress_of_the_user(page, deck_dir, make_apkg):
    add_deck(deck_dir, make_apkg, [("guid-coffee", "I drink coffee.", "Pijem kavu.")])
    answer_as(routes.LOCAL_USER, 3)
    answer_as("user-2", 1)
    page.goto("/#progress")
    expect(page.locator("#stats-table tr").first).to_have_text("Answers1")
    expect(page.locator("#stats-days .day")).to_have_count(90)
    expect(page.locator("#stats-rate .day")).to_have_count(90)
    # Today is the last bar: 1 of 1 was not "Again".
    assert "100%" in page.locator("#stats-rate .day").last.get_attribute("title")
    # Not an admin: no other user.
    expect(page.locator("#progress-user option")).to_have_text(["My cards"])


def test_an_admin_selects_another_user(page, deck_dir, make_apkg):
    add_deck(deck_dir, make_apkg, [("guid-coffee", "I drink coffee.", "Pijem kavu.")])
    answer_as(routes.LOCAL_USER, 3)
    answer_as("user-2", 1)
    store.save_user("user-2", "Ana")
    service.app.dependency_overrides[routes.is_admin] = lambda: True
    try:
        page.goto("/#progress")
        expect(page.locator("#progress-user option")).to_have_text(["My cards", "Ana"])
        expect(page.locator("#stats-table tr").nth(1)).to_have_text('Not "Again"100%')
        page.locator("#progress-user").select_option("user-2")
        expect(page.locator("#stats-table tr").nth(1)).to_have_text('Not "Again"0%')
    finally:
        service.app.dependency_overrides.pop(routes.is_admin)


def test_the_flow_of_a_card(page, deck_dir, make_apkg):
    add_deck(deck_dir, make_apkg, [("guid-coffee", "I drink coffee.", "Pijem kavu.")])
    page.goto("/#cards")
    page.locator("button.deck").click()
    expect(page.locator("#card-task")).to_have_text("Enter this in Croatian.")
    expect(page.locator("#card")).to_contain_text("coffee")
    expect(page.locator("#answered")).to_be_hidden()
    # The font of a script comes from the language of the line.
    expect(page.locator("#card-result .sentence").first).to_have_attribute("lang", "en")

    # In an input method, Enter accepts a word, and must not send the answer.
    enter = """(composing) => !document.getElementById("answer").dispatchEvent(
        new KeyboardEvent("keydown", {key: "Enter", isComposing: composing,
                                      cancelable: true, bubbles: true}))"""
    assert page.evaluate(enter, True) is True
    assert page.evaluate(enter, False) is False

    # One wrong letter: Hard.
    page.locator("#answer").fill("Pijem kava.")
    page.locator("#check").click()
    # The answer runs the light models, so the first one takes a moment.
    expect(page.locator("#answered")).to_be_visible(timeout=60_000)
    expect(page.locator("#diff")).to_contain_text("kav")
    expect(page.locator("#diff")).to_have_attribute("lang", "hr")
    expect(page.locator("#ratings button.current")).to_have_text("2 Hard")

    # A browser with no voices must say so, and not stay silent.
    page.evaluate("speechSynthesis.getVoices = () => []")
    page.locator("#speak").click()
    expect(page.locator("#cards-status")).to_contain_text("has no voices")

    page.locator("#ratings button[data-rating='3']").click()
    expect(page.locator("#ratings button.current")).to_have_text("3 Good")
    page.locator("#next").click()
    expect(page.locator("#card-task")).to_contain_text("No more cards for now.")


def test_no_questions_to_the_ai_with_no_key(page, deck_dir, make_apkg, backend):
    backend.key = False
    add_deck(deck_dir, make_apkg, [("guid-coffee", "I drink coffee.", "Pijem kavu.")])
    page.goto("/#cards")
    page.locator("button.deck").click()
    page.locator("#give-up").click()
    expect(page.locator("#answered")).to_be_visible(timeout=60_000)
    expect(page.locator("#card-explain")).to_be_hidden()


def test_a_question_to_the_ai(page, deck_dir, make_apkg, backend, monkeypatch):
    # The model can write anything: the page must show it as text.
    monkeypatch.setattr(
        backend, "complete", lambda system, prompt: "<b>kavu</b> is the\naccusative."
    )
    add_deck(deck_dir, make_apkg, [("guid-coffee", "I drink coffee.", "Pijem kavu.")])
    page.goto("/#cards")
    page.locator("button.deck").click()
    expect(page.locator("#card-explain")).to_be_hidden()
    page.locator("#answer").fill("Pijem kava.")
    page.locator("#check").click()
    expect(page.locator("#answered")).to_be_visible(timeout=60_000)
    # A card has the questions about an answer and those about a sentence.
    expect(page.locator("#card-explain button")).to_have_count(6)
    page.locator("#card-explain input").fill("why not kava?")
    page.locator("#card-explain button[data-question=why_wrong]").click()
    expect(page.locator("#card-explain .explain-text")).to_have_text(
        "<b>kavu</b> is the\naccusative.", use_inner_text=True
    )
    expect(page.locator("#card-explain b")).to_have_count(0)
    expect(page.locator("#card-explain .sub").last).to_contain_text("fake-model")
    # The next card has no answer yet, and so no questions.
    page.locator("#next").click()
    expect(page.locator("#card-explain")).to_be_hidden()

    # The other tab has only the questions about a sentence.
    page.goto("/")
    page.locator("#text").fill("Idemo na kavu.")
    page.locator("#go").click()
    expect(page.locator("#explain button")).to_have_count(3)


def ask_why_wrong(page, deck_dir, make_apkg):
    """Answer a card, then ask the AI about it. The button of the question."""
    add_deck(deck_dir, make_apkg, [("guid-coffee", "I drink coffee.", "Pijem kavu.")])
    page.goto("/#cards")
    page.locator("button.deck").click()
    page.locator("#answer").fill("Pijem kava.")
    page.locator("#check").click()
    expect(page.locator("#answered")).to_be_visible(timeout=60_000)
    button = page.locator("#card-explain button[data-question=why_wrong]")
    button.click()
    return button


def test_a_question_to_the_ai_again_after_an_error(
    new_page, deck_dir, make_apkg, backend, monkeypatch
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
    button = ask_why_wrong(page, deck_dir, make_apkg)
    expect(page.locator("#card-explain .explain-text.error")).to_contain_text("502")
    button.click()
    expect(page.locator("#card-explain .explain-text")).to_have_text("It is fine.")


def test_a_question_to_the_ai_with_no_answer(
    page, deck_dir, make_apkg, backend, monkeypatch
):
    """A proxy can hold the request with no answer. The page stops it, and the
    user can ask again."""
    release = threading.Event()
    answers = iter([None, "It is fine."])

    def complete(system, prompt, **kwargs):
        answer = next(answers)
        if answer is None:
            release.wait(timeout=30)
            raise explain.ExplainError("too late")
        return answer

    monkeypatch.setattr(backend, "complete", complete)
    page.add_init_script("addEventListener('load', () => { explainTimeoutMs = 500; })")
    try:
        button = ask_why_wrong(page, deck_dir, make_apkg)
        expect(page.locator("#card-explain .explain-text.error")).to_have_text(
            "No answer after 1 s. Try again."
        )
        expect(button).to_be_enabled()
        button.click()
        expect(page.locator("#card-explain .explain-text")).to_have_text("It is fine.")
    finally:
        release.set()


def test_a_language_from_right_to_left(page, deck_dir, make_apkg):
    # No language of the app has such a script, so the page gets Croatian as
    # one. The direction comes only from the language list.
    add_deck(deck_dir, make_apkg, [("guid-coffee", "I drink coffee.", "Pijem kavu.")])
    page.goto("/#cards")
    page.locator("button.deck").click()
    expect(page.locator("#answer")).to_have_attribute("dir", "ltr")
    page.evaluate("languages.hr.direction = 'rtl'")

    page.locator("#answer").fill("Pijem kavu.")
    page.locator("#check").click()
    expect(page.locator("#answered")).to_be_visible(timeout=60_000)
    expect(page.locator("#diff")).to_have_attribute("dir", "rtl")
    # The typed answer is the first line, and the English prompt is under it.
    lines = page.locator("#card-result .sentence")
    expect(lines.nth(0)).to_have_attribute("dir", "rtl")
    expect(lines.nth(1)).to_have_attribute("dir", "ltr")
    # The first word is on the right.
    chips = lines.nth(0).locator(".chip")
    assert chips.nth(0).bounding_box()["x"] > chips.nth(1).bounding_box()["x"]

    # The entry field of the other tab follows the side that the user enters.
    page.goto("/")
    # The language list comes a moment after the page.
    page.wait_for_function("languages.hr")
    page.evaluate("languages.hr.direction = 'rtl'; showSource()")
    expect(page.locator("#text")).to_have_attribute("dir", "rtl")
    page.locator("input[name=source][value=en]").check()
    expect(page.locator("#text")).to_have_attribute("dir", "ltr")


def test_the_accent_note_follows_the_language_of_the_deck(page, deck_dir, make_apkg):
    make_apkg(
        deck_dir / "german.apkg", [("guid-tea", "I drink tea.", "Ich trinke Tee.")]
    )
    german = TOML.replace('"Basics"', '"Deutsch"').replace('"hr"', '"de"')
    (deck_dir / "german.toml").write_text(german, encoding="utf-8")
    add_deck(deck_dir, make_apkg, [("guid-coffee", "I drink coffee.", "Pijem kavu.")])
    accents = page.locator("#accents")
    # The breakdown tab has Croatian, the first language.
    page.goto("/")
    expect(accents).to_be_visible()
    page.get_by_role("button", name="Flashcards").click()
    expect(accents).to_be_hidden()
    page.locator("button.deck", has_text="Deutsch").click()
    expect(page.locator("#card")).to_contain_text("tea")
    expect(accents).to_be_hidden()
    page.locator("#to-decks").click()
    page.locator("button.deck", has_text="Basics").click()
    expect(page.locator("#card")).to_contain_text("coffee")
    expect(accents).to_be_visible()
    page.get_by_role("button", name="Breakdown").click()
    page.locator("#language").select_option("de")
    expect(accents).to_be_hidden()
    # The deck is still Croatian.
    page.get_by_role("button", name="Flashcards").click()
    expect(accents).to_be_visible()


def test_the_subdecks_are_a_tree(page, deck_dir, make_apkg):
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
    page.goto("/#cards")
    expect(page.locator(".deck-heading h3")).to_have_text(["Basics"])
    expect(page.locator(".deck-heading h4")).to_have_text(["Read", "Speak"])
    expect(page.locator(".deck-heading").first).to_contain_text("3 decks · 3 new")
    expect(page.locator("button.deck strong")).to_have_text(["2", "3", "2"])
    page.locator("button.deck").first.click()
    expect(page.locator("#deck-name")).to_have_text("Basics › Read › 2")
    # A note type for reading shows the Croatian.
    expect(page.locator("#card-task")).to_have_text("Enter this in English.")
    expect(page.locator("#card")).to_contain_text("Pijem")


def test_a_card_with_a_picture_and_a_clip(page, deck_dir, make_apkg):
    notes = [("guid-house", '<img src="my house.png">', "kuća[sound:kuća.mp3]")]
    media = {"my house.png": PNG, "kuća.mp3": b"a clip"}
    add_deck(deck_dir, make_apkg, notes, new_format=True, media=media)
    page.goto("/#cards")
    page.locator("button.deck").click()
    expect(page.locator("#card-task")).to_have_text(
        "Enter what you see or hear in Croatian."
    )
    picture = page.locator("#card-media img")
    expect(picture).to_have_count(1)
    # The file came through the media route, and it is a picture.
    expect(picture).to_have_js_property("naturalWidth", 1)
    expect(page.locator("#answer-media > *")).to_have_count(0)

    page.locator("#answer").fill("kuća")
    page.locator("#check").click()
    expect(page.locator("#answered")).to_be_visible(timeout=60_000)
    expect(page.locator("#ratings button.current")).to_have_text("3 Good")
    clip = page.locator("#answer-media audio")
    expect(clip).to_have_count(1)
    assert "/media/ku%C4%87a.mp3" in clip.get_attribute("src")
