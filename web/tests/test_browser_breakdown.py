"""The Breakdown tab and the Listen panel of the Flutter app in a real
browser, with the real light models, a fake translator and a fake voice
service. The browser fixtures are in conftest.py."""

import re

import pytest
from playwright.sync_api import expect
from tlhelper import speech, translators

TITLE = "Croatian sentence breakdown"


class FakeTranslator:
    name = "fake"

    def translate(self, text, source, target):
        return {
            "I am going to the islands.": "Idem na otoke.",
            "Idem na otoke.": "I am going to the islands.",
            "Ona je je bila kod kuće.": "She was at home.",
        }[text]


# A silent MPEG-1 layer III frame (128 kbit/s, 44.1 kHz, 417 bytes), a few
# times: the browser plays it with no error.
SILENT_MP3 = (b"\xff\xfb\x90\x00" + b"\x00" * 413) * 8


class FakeSynthesizer:
    name = "fake"

    def __init__(self):
        self.calls = []

    def available(self):
        return True

    def model(self):
        return "fake-voice"

    def languages(self):
        return ["hr", "en"]

    def synthesize(self, text, language):
        self.calls.append((text, language))
        return SILENT_MP3


@pytest.fixture(autouse=True)
def translator(monkeypatch):
    monkeypatch.setitem(translators.TRANSLATORS, "fake", FakeTranslator())
    monkeypatch.setenv("TRANSLATOR", "fake")


@pytest.fixture
def voice(monkeypatch):
    fake = FakeSynthesizer()
    monkeypatch.setitem(speech.SYNTHESIZERS, "fake", fake)
    monkeypatch.setenv("TLHELPER_VOICE_BACKEND", "fake")
    return fake


@pytest.fixture
def breakdown(type_into):
    """breakdown(page, text, last, english=False, translate=False): enter a
    text and wait for the chip "chip: <last>" of its breakdown."""

    def enter(page, text, last, *, english=False, translate=False):
        page.goto("/")
        page.get_by_role("heading", name=TITLE).wait_for()
        # The first request waits for the load of the light models.
        type_into(page.get_by_role("textbox", name="Time limit"), "60")
        if english:
            page.get_by_role("radio", name=re.compile("^I enter English")).click()
        if translate:
            page.get_by_role("checkbox", name="Translate to English").click()
        type_into(page.get_by_role("textbox").first, text)
        page.get_by_role("button", name=f"chip: {last}").wait_for(timeout=60_000)

    return enter


def chips(page):
    """The labels of the chips, from the top left to the bottom right."""
    found = page.get_by_role("button", name=re.compile("^chip: "))
    # Flutter puts the label of a button in its text, not in aria-label.
    boxes = [
        (box["y"], box["x"], each.text_content().strip())
        for each in found.all()
        if (box := each.bounding_box())
    ]
    return [label for _, _, label in sorted(boxes)]


def test_a_croatian_sentence(page, breakdown, note):
    breakdown(page, "Idem na otoke.", ". PUNCT")
    expect(
        page.get_by_role("checkbox", name=re.compile("^Large models"))
    ).not_to_be_checked()
    assert chips(page) == [
        "chip: Idem VERB",
        "chip: na ADP",
        "chip: otoke NOUN",
        "chip: . PUNCT",
    ]
    otoke = page.get_by_role("button", name="chip: otoke NOUN")
    otoke.click()
    expect(otoke).to_have_attribute("aria-current", "true")
    page.get_by_role("heading", name="otoke").wait_for()
    note(page, "otok").wait_for()
    note(page, re.compile("accusative")).wait_for()
    note(page, re.compile("Case=Acc")).wait_for()


def test_a_croatian_determiner_and_pronoun(page, breakdown):
    breakdown(page, "Vidim moju kuću. Vidim nju.", "nju PRON")
    labels = chips(page)
    assert labels[1] == "chip: moju DET"
    assert labels[5] == "chip: nju PRON"


@pytest.mark.parametrize("width", [390, 1280])
def test_an_english_sentence(new_page, breakdown, note, screenshot, width):
    page = new_page(width=width)
    breakdown(page, "I am going to the islands.", "otoke NOUN", english=True)
    # The English text is on top, and the Croatian translation is under it.
    labels = chips(page)
    assert labels[:7] == [
        "chip: I PRON",
        "chip: am AUX",
        "chip: going VERB",
        "chip: to ADP",
        "chip: the DET",
        "chip: islands NOUN",
        "chip: . PUNCT",
    ]
    assert labels[7:] == [
        "chip: Idem VERB",
        "chip: na ADP",
        "chip: otoke NOUN",
        "chip: . PUNCT",
    ]
    note(page, "Croatian: Idem na otoke.").wait_for()
    # The curves between the two lines.
    links = note(page, re.compile(r"^links: \d+$"))
    links.wait_for()
    assert int(links.text_content().split()[1]) >= 3
    screenshot(page, f"english-{width}")


@pytest.mark.parametrize("width", [390, 1280])
def test_a_problem_of_the_grammar(new_page, breakdown, note, width):
    page = new_page(width=width)
    breakdown(page, "Ona je je bila kod kuće.", "She PRON", translate=True)
    page.get_by_role("button", name="chip: je AUX").last.click()
    note(page, re.compile("'je' repeats.")).wait_for()


def test_no_listen_buttons_without_a_voice_service(page, breakdown):
    breakdown(page, "Idem na otoke.", ". PUNCT")
    expect(page.get_by_role("button", name="Croatian", exact=True)).to_have_count(0)


@pytest.mark.parametrize("width", [390, 1280])
def test_the_listen_panel(new_page, breakdown, note, voice, screenshot, width):
    page = new_page(width=width)
    breakdown(page, "Idem na otoke.", "islands NOUN", translate=True)
    # The text goes to the voice service only on a click.
    assert voice.calls == []
    expect(page.get_by_role("button", name="Play", exact=True)).to_have_count(0)
    croatian = page.get_by_role("button", name="Croatian", exact=True)
    english = page.get_by_role("button", name="English", exact=True)
    croatian.click()
    note(page, "fake-voice read this.").wait_for()
    # The sound plays at once, and its player stays on the panel.
    page.get_by_role("button", name=re.compile("^(Play|Pause)$")).wait_for()
    english.click()
    expect(english).to_be_enabled()
    expect(croatian).to_be_enabled()
    assert voice.calls == [
        ("Idem na otoke.", "hr"),
        ("I am going to the islands.", "en"),
    ]
    screenshot(page, f"listen-{width}")


def test_large_models_by_default(page, monkeypatch):
    monkeypatch.setenv("TLHELPER_ALWAYS_LARGE", "1")
    heavy = page.get_by_role("checkbox", name=re.compile("^Large models"))
    page.goto("/")
    page.get_by_role("heading", name=TITLE).wait_for()
    expect(heavy).to_be_checked()
    # The choice of the user wins over the default of the server.
    heavy.click()
    expect(heavy).not_to_be_checked()
    page.reload()
    page.get_by_role("heading", name=TITLE).wait_for()
    expect(heavy).not_to_be_checked()
